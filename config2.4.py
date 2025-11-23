import yaml
import sys
import os
import urllib.request
import xml.etree.ElementTree as ET
import ssl
import argparse
from typing import List, Dict, Set
from collections import deque, defaultdict

# Обход SSL ошибки
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

def parse_arguments():
    parser = argparse.ArgumentParser(description='Maven Dependency Analyzer')
    parser.add_argument('config_file', 
                       nargs='?',
                       default='config_test.yaml',
                       help='Path to config file (default: config_test.yaml)')
    parser.add_argument('--list', '-l', action='store_true',
                       help='List available config files')
    return parser.parse_args()

def list_available_configs():
    configs = [f for f in os.listdir('.') if f.startswith('config_') and f.endswith('.yaml')]
    if configs:
        print("Доступные конфигурационные файлы:")
        for config in configs:
            print(f"  - {config}")
    else:
        print("Конфигурационные файлы не найдены")
    return configs

class MavenDependencyAnalyzer:
    def __init__(self):
        self.config = {}
        self.test_repo_data = None
        self.dependency_graph = {}
        
    def load_config(self, config_file: str) -> Dict:
        try:
            with open(config_file, 'r') as file:
                config = yaml.safe_load(file)
                if config is None:
                    raise Exception(f"{config_file} пустой")
                print(f"Загружена конфигурация из: {config_file}")
                return config
        except FileNotFoundError:
            raise Exception(f"Файл {config_file} не найден")
        except yaml.YAMLError as e:
            raise Exception(f"Ошибка в формате YAML в {config_file}: {e}")
    
    def validate_config(self, config: Dict) -> bool:
        required_fields = {
            'package_name': str,
            'repository_url': str,
            'test_mode': bool,
            'ascii_tree': bool,
            'max_depth': int
        }
        
        for field, field_type in required_fields.items():
            if field not in config:
                raise Exception(f"Отсутствует обязательное поле '{field}'")
            
            if not isinstance(config[field], field_type):
                raise Exception(f"Поле '{field}' должно быть типа {field_type.__name__}")
        
        if config['max_depth'] < 1:
            raise Exception("max_depth должен быть целым числом больше 0")
        
        if not config['package_name'].strip():
            raise Exception("package_name не может быть пустым")
        
        # Для тестового режима проверяем существование файла репозитория
        if config['test_mode'] and not config['repository_url'].startswith(('http://', 'https://')):
            repo_path = config['repository_url']
            if not os.path.exists(repo_path):
                raise Exception(f"Файл тестового репозитория '{repo_path}' не найден")
        
        return True
    
    def load_test_repository(self) -> Dict:
        if self.test_repo_data is not None:
            return self.test_repo_data
            
        repo_path = self.config['repository_url']
        try:
            with open(repo_path, 'r') as f:
                self.test_repo_data = yaml.safe_load(f)
            
            # Валидация структуры тестового репозитория
            if not isinstance(self.test_repo_data, dict):
                raise Exception("Тестовый репозиторий должен быть в формате словаря")
                
            # Проверяем что все пакеты - большие латинские буквы
            for package_name in self.test_repo_data.keys():
                if not (isinstance(package_name, str) and len(package_name) == 1 and package_name.isupper()):
                    raise Exception(f"Пакет '{package_name}' должен быть одной большой латинской буквой")
            
            print(f"Загружен тестовый репозиторий: {len(self.test_repo_data)} пакетов")
            return self.test_repo_data
            
        except Exception as e:
            raise Exception(f"Ошибка загрузки тестового репозитория: {e}")
    
    def build_dependency_graph(self) -> Dict:
        start_package = self.config['package_name']
        max_depth = self.config['max_depth']
        
        print(f"Построение графа зависимостей для '{start_package}'")
        print(f"Максимальная глубина: {max_depth}")
        
        # Для тестового режима проверяем корректность имени пакета
        if self.config['test_mode'] and not self.config['repository_url'].startswith(('http://', 'https://')):
            if not (len(start_package) == 1 and start_package.isupper()):
                raise Exception(f"В тестовом режиме имя пакета должно быть одной большой латинской буквой, получено: '{start_package}'")
        
        queue = deque([(start_package, 0)])
        visited = set()
        dependency_graph = {}
        
        while queue:
            current_package, depth = queue.popleft()
            
            if current_package in visited:
                continue
                
            visited.add(current_package)
            
            if depth < max_depth:
                dependencies = self.get_package_dependencies(current_package)
                dependency_graph[current_package] = dependencies
                
                for dep in dependencies:
                    if dep not in visited:
                        queue.append((dep, depth + 1))
            else:
                dependency_graph[current_package] = []
        
        self.dependency_graph = dependency_graph
        return dependency_graph
    
    def get_package_dependencies(self, package_name: str) -> List[str]:
        if self.config['test_mode']:
            return self._get_test_dependencies(package_name)
        else:
            return self._get_real_dependencies(package_name)
    
    def _get_test_dependencies(self, package_name: str) -> List[str]:
        # Если указан путь к файлу тестового репозитория
        if not self.config['repository_url'].startswith(('http://', 'https://')):
            test_data = self.load_test_repository()
            return test_data.get(package_name, [])
        test_data_maven = {
            "org.springframework:spring-core": ["org.springframework:spring-jcl", "commons-logging:commons-logging"],
            "org.springframework:spring-jcl": [],
            "commons-logging:commons-logging": [],
        }
        return test_data_maven.get(package_name, [])
    
    def _get_real_dependencies(self, package_name: str) -> List[str]:
        try:
            if ':' not in package_name:
                return []
                
            group_id, artifact_id = package_name.split(':', 1)
            base_url = self.config['repository_url'].rstrip('/')
            
            metadata_url = f"{base_url}/{group_id.replace('.', '/')}/{artifact_id}/maven-metadata.xml"
            
            with urllib.request.urlopen(metadata_url, context=ssl_context) as response:
                metadata_content = response.read().decode('utf-8')
            
            version = self._parse_latest_version(metadata_content)
            if not version:
                return []
            
            pom_url = f"{base_url}/{group_id.replace('.', '/')}/{artifact_id}/{version}/{artifact_id}-{version}.pom"
            
            with urllib.request.urlopen(pom_url, context=ssl_context) as response:
                pom_content = response.read().decode('utf-8')
            
            dependencies = self._parse_pom_dependencies(pom_content)
            return dependencies
            
        except Exception as e:
            print(f"    Ошибка получения зависимостей для {package_name}: {e}")
            return []
    
    def _parse_latest_version(self, metadata_content: str) -> str:
        try:
            root = ET.fromstring(metadata_content)
            versioning = root.find('versioning')
            if versioning is not None:
                latest = versioning.find('latest')
                if latest is not None:
                    return latest.text
            versions = root.find('versioning/versions')
            if versions is not None and len(versions) > 0:
                return versions[0].text
            return ""
        except Exception:
            return ""
    
    def _parse_pom_dependencies(self, pom_content: str) -> List[str]:
        try:
            root = ET.fromstring(pom_content)
            dependencies = []
            ns = {'maven': 'http://maven.apache.org/POM/4.0.0'}
            
            for dep in root.findall('.//maven:dependency', ns):
                group_id_elem = dep.find('maven:groupId', ns)
                artifact_id_elem = dep.find('maven:artifactId', ns)
                
                if group_id_elem is not None and artifact_id_elem is not None:
                    dependency_str = f"{group_id_elem.text}:{artifact_id_elem.text}"
                    dependencies.append(dependency_str)
            
            return dependencies
        except Exception:
            return []
    
    def detect_cycles(self, graph: Dict) -> List[List[str]]:
        def dfs(node, path, visited, cycles):
            if node in path:
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                # Проверяем что цикл уникален
                cycle_str = '->'.join(cycle)
                if cycle_str not in seen_cycles:
                    seen_cycles.add(cycle_str)
                    cycles.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, []):
                dfs(neighbor, path.copy(), visited, cycles)
        
        visited = set()
        all_cycles = []
        seen_cycles = set()
        
        for node in graph:
            if node not in visited:
                dfs(node, [], visited, all_cycles)
        
        return all_cycles
    
    def print_dependency_tree(self, graph: Dict):
        print(f"\nДЕРЕВО ЗАВИСИМОСТЕЙ:")
        
        visited_in_tree = set()
        
        def print_node(package, prefix="", is_last=True):
            if package in visited_in_tree:
                print(f"{prefix}└── {package} [ЦИКЛ]")
                return
                
            visited_in_tree.add(package)
            print(f"{prefix}└── {package}" if is_last else f"{prefix}├── {package}")
            
            dependencies = graph.get(package, [])
            if not dependencies:
                return
                
            new_prefix = prefix + ("    " if is_last else "│   ")
            
            for i, dep in enumerate(dependencies):
                is_last_dep = (i == len(dependencies) - 1)
                print_node(dep, new_prefix, is_last_dep)
        
        print_node(self.config['package_name'])

    def get_load_order(self) -> List[str]:
        if not self.dependency_graph:
            return []
        
        all_packages = set()
        for pkg, deps in self.dependency_graph.items():
            all_packages.add(pkg)
            all_packages.update(deps)
        
        full_graph = defaultdict(list)
        for pkg in all_packages:
            if pkg in self.dependency_graph:
                full_graph[pkg] = self.dependency_graph[pkg]
            else:
                full_graph[pkg] = []
        
        in_degree = defaultdict(int)
        for pkg in all_packages:
            in_degree[pkg] = 0
            
        for pkg, deps in full_graph.items():
            for dep in deps:
                in_degree[dep] += 1
        
        load_order = []
        queue = deque([pkg for pkg in all_packages if in_degree[pkg] == 0])
        
        while queue:
            current = queue.popleft()
            load_order.append(current)
            
            for neighbor in full_graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(load_order) != len(all_packages):
            remaining_packages = [pkg for pkg in all_packages if pkg not in load_order]
            load_order.extend(remaining_packages)
        
        return load_order

    def print_load_order(self):
        load_order = self.get_load_order()
        
        if not load_order:
            print("Зависимости не найдены")
            return
        
        print(f"\nПОРЯДОК ЗАГРУЗКИ ЗАВИСИМОСТЕЙ:")
        for i, pkg in enumerate(load_order, 1):
            print(f"{i}. {pkg}")

    def run(self, config_file: str):
        try:
            print("Этап 4. Дополнительные операции\n")
            
            config = self.load_config(config_file)
            self.validate_config(config)
            self.config = config
            
            # Особенности тестового режима
            if config['test_mode'] and not config['repository_url'].startswith(('http://', 'https://')):
                print(f"РЕЖИМ: Тестовый репозиторий из файла")
                print(f"Файл: {config['repository_url']}")
                self.load_test_repository()
            elif config['test_mode']:
                print(f"РЕЖИМ: Тестовые данные (встроенные)")
            else:
                print(f"РЕЖИМ: Реальный Maven репозиторий")
            
            print(f"\nПОСТРОЕНИЕ ГРАФА ЗАВИСИМОСТЕЙ:")
            dependency_graph = self.build_dependency_graph()
            
            # ASCII дерево (если включено в конфиге)
            if self.config['ascii_tree'] and dependency_graph:
                self.print_dependency_tree(dependency_graph)
            elif not dependency_graph:
                print("Граф зависимостей пуст")
            
            # Обнаружение циклов
            cycles = self.detect_cycles(dependency_graph)
            if cycles:
                print(f"\nОБНАРУЖЕНЫ ЦИКЛИЧЕСКИЕ ЗАВИСИМОСТИ:")
                for i, cycle in enumerate(cycles, 1):
                    print(f"{i}. {' -> '.join(cycle)}")
            
            # Порядок загрузки зависимостей
            self.print_load_order()
            
            
        except KeyboardInterrupt:
            print("\nПрограмма прервана пользователем")
            sys.exit(1)
        except Exception as e:
            print(f"\nОШИБКА: {e}")
            sys.exit(1)

def main():
    args = parse_arguments()
    
    if args.list:
        list_available_configs()
        return
    
    analyzer = MavenDependencyAnalyzer()
    analyzer.run(args.config_file)

if __name__ == "__main__":
    main()

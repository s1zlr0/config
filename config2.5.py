import yaml
import sys
import os
import urllib.request
import xml.etree.ElementTree as ET
import ssl
from typing import List, Dict, Set
from collections import deque, defaultdict
import tkinter as tk
from tkinter import ttk
import math

# Обход SSL ошибки
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

class MavenDependencyAnalyzer:
    def __init__(self, config: Dict):
        self.config = config
        self.test_repo_data = None
        self.dependency_graph = {}
        
    def load_config(self) -> Dict:
        try:
            with open('config.yaml', 'r') as file:
                config = yaml.safe_load(file)
                if config is None:
                    raise Exception("config.yaml пустой")
                return config
        except FileNotFoundError:
            raise Exception("Файл config.yaml не найден")
        except yaml.YAMLError as e:
            raise Exception(f"Ошибка в формате YAML: {e}")
    
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
            
            if not isinstance(self.test_repo_data, dict):
                raise Exception("Тестовый репозиторий должен быть в формате словаря")
                
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
        
        print("\nХод анализа:")
        
        while queue:
            current_package, depth = queue.popleft()
            
            if current_package in visited:
                print(f"  Пропускаем {current_package} (уже посещен)")
                continue
                
            visited.add(current_package)
            print(f"  Глубина {depth}: анализируем {current_package}")
            
            if depth < max_depth:
                dependencies = self.get_package_dependencies(current_package)
                dependency_graph[current_package] = dependencies
                
                for dep in dependencies:
                    if dep not in visited:
                        queue.append((dep, depth + 1))
            else:
                dependency_graph[current_package] = []
                print(f"    Достигнута максимальная глубина {max_depth}")
        
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
        
        # Резервные тестовые данные (для обратной совместимости)
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


    def generate_mermaid_graph(self) -> str:
        if not self.dependency_graph:
            return "graph TD\n    A[Нет зависимостей]"
        
        mermaid_lines = ["graph TD"]
        visited_nodes = set()
        
        for package, dependencies in self.dependency_graph.items():
            # Экранируем специальные символы для Mermaid
            safe_package = package.replace(':', '_').replace('-', '_').replace('.', '_')
            if safe_package not in visited_nodes:
                mermaid_lines.append(f"    {safe_package}[{package}]")
                visited_nodes.add(safe_package)
            
            for dep in dependencies:
                safe_dep = dep.replace(':', '_').replace('-', '_').replace('.', '_')
                if safe_dep not in visited_nodes:
                    mermaid_lines.append(f"    {safe_dep}[{dep}]")
                    visited_nodes.add(safe_dep)
                
                mermaid_lines.append(f"    {safe_package} --> {safe_dep}")
        
        return "\n".join(mermaid_lines)

    def create_tkinter_graph(self):
        if not self.dependency_graph:
            print("Нет данных для построения графа")
            return
        
        try:
            # Создаем главное окно
            root = tk.Tk()
            root.title(f"Граф зависимостей: {self.config['package_name']}")
            root.geometry("1000x700")
            
            # Создаем canvas для рисования
            canvas = tk.Canvas(root, bg="white", scrollregion=(0, 0, 2000, 2000))
            
            # Добавляем скроллбары
            v_scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
            h_scrollbar = ttk.Scrollbar(root, orient="horizontal", command=canvas.xview)
            canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
            
            # Размещаем элементы
            canvas.grid(row=0, column=0, sticky="nsew")
            v_scrollbar.grid(row=0, column=1, sticky="ns")
            h_scrollbar.grid(row=1, column=0, sticky="ew")
            
            root.grid_rowconfigure(0, weight=1)
            root.grid_columnconfigure(0, weight=1)
            
            # Параметры для рисования
            node_radius = 60
            level_height = 150
            node_width = 120
            node_height = 40
            
            # Располагаем узлы графа
            positions = {}
            level_nodes = defaultdict(list)
            
            # Определяем уровни для каждого узла
            def calculate_levels():
                levels = {}
                queue = deque([(self.config['package_name'], 0)])
                visited = set()
                
                while queue:
                    node, level = queue.popleft()
                    if node in visited:
                        continue
                    visited.add(node)
                    levels[node] = level
                    level_nodes[level].append(node)
                    
                    for dep in self.dependency_graph.get(node, []):
                        if dep not in visited:
                            queue.append((dep, level + 1))
                
                return levels
            
            levels = calculate_levels()
            
            # Вычисляем позиции для каждого узла
            x_start = 100
            y_start = 100
            
            for level in sorted(level_nodes.keys()):
                nodes_in_level = level_nodes[level]
                level_width = len(nodes_in_level) * (node_width + 50)
                x_positions = []
                
                for i, node in enumerate(nodes_in_level):
                    x = x_start + (i + 0.5) * (node_width + 50)
                    y = y_start + level * level_height
                    positions[node] = (x, y)
            
            # Рисуем связи
            for package, dependencies in self.dependency_graph.items():
                if package in positions:
                    x1, y1 = positions[package]
                    for dep in dependencies:
                        if dep in positions:
                            x2, y2 = positions[dep]
                            canvas.create_line(x1, y1 + node_height/2, x2, y2 - node_height/2, 
                                            arrow=tk.LAST, arrowshape=(8, 10, 5), width=2, fill="gray")
            
            # Рисуем узлы
            for node, (x, y) in positions.items():
                # Основной пакет - другой цвет
                if node == self.config['package_name']:
                    color = "lightblue"
                else:
                    color = "lightgreen"
                
                # Рисуем прямоугольник
                canvas.create_rectangle(x - node_width/2, y - node_height/2, 
                                      x + node_width/2, y + node_height/2,
                                      fill=color, outline="black", width=2)
                
                # Добавляем текст (обрезаем если слишком длинный)
                display_text = node
                if len(node) > 20:
                    display_text = node[:17] + "..."
                
                canvas.create_text(x, y, text=display_text, font=("Arial", 8), width=node_width-10)
            
            # Добавляем легенду
            legend_x = 50
            legend_y = 50
            
            canvas.create_rectangle(legend_x, legend_y, legend_x + 20, legend_y + 20, 
                                  fill="lightblue", outline="black")
            canvas.create_text(legend_x + 40, legend_y + 10, text="Основной пакет", 
                             anchor="w", font=("Arial", 9))
            
            canvas.create_rectangle(legend_x + 150, legend_y, legend_x + 170, legend_y + 20, 
                                  fill="lightgreen", outline="black")
            canvas.create_text(legend_x + 190, legend_y + 10, text="Зависимости", 
                             anchor="w", font=("Arial", 9))
            
            # Добавляем информацию о графе
            info_text = f"Всего узлов: {len(positions)} | Всего связей: {sum(len(deps) for deps in self.dependency_graph.values())}"
            canvas.create_text(500, 30, text=info_text, font=("Arial", 10, "bold"))
            
            # Запускаем главный цикл
            print("\nОткрыто графическое окно с графом зависимостей")
            print("Закройте окно для продолжения работы программы")
            root.mainloop()
            
        except Exception as e:
            print(f"Ошибка при создании графического представления: {e}")

    def create_tkinter_graph(self):
        """Создает графическое представление графа с помощью tkinter"""
        if not self.dependency_graph:
            print("Нет данных для построения графа")
            return
        
        try:
            # Создаем главное окно
            root = tk.Tk()
            root.title(f"Граф зависимостей: {self.config['package_name']}")
            root.geometry("1200x800")
            
            # Создаем фрейм для canvas и скроллбаров
            main_frame = ttk.Frame(root)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Создаем canvas для рисования
            canvas = tk.Canvas(main_frame, bg="white")
            
            # Добавляем скроллбары
            v_scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
            h_scrollbar = ttk.Scrollbar(main_frame, orient="horizontal", command=canvas.xview)
            canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
            
            # Размещаем элементы
            canvas.grid(row=0, column=0, sticky="nsew")
            v_scrollbar.grid(row=0, column=1, sticky="ns")
            h_scrollbar.grid(row=1, column=0, sticky="ew")
            
            main_frame.grid_rowconfigure(0, weight=1)
            main_frame.grid_columnconfigure(0, weight=1)
            
            # Параметры для рисования (адаптивные)
            total_nodes = sum(len(deps) for deps in self.dependency_graph.values()) + len(self.dependency_graph)
            
            # Адаптируем размеры в зависимости от количества узлов
            if total_nodes > 20:
                node_width = 100
                node_height = 30
                level_height = 120
                font_size = 7
            elif total_nodes > 10:
                node_width = 120
                node_height = 35
                level_height = 140
                font_size = 8
            else:
                node_width = 140
                node_height = 40
                level_height = 160
                font_size = 9
            
            # Располагаем узлы графа
            positions = {}
            level_nodes = defaultdict(list)
            
            # Определяем уровни для каждого узла с помощью BFS
            def calculate_levels():
                levels = {}
                queue = deque([(self.config['package_name'], 0)])
                visited = set()
                
                while queue:
                    node, level = queue.popleft()
                    if node in visited:
                        continue
                    visited.add(node)
                    levels[node] = level
                    level_nodes[level].append(node)
                    
                    for dep in self.dependency_graph.get(node, []):
                        if dep not in visited:
                            queue.append((dep, level + 1))
                
                # Добавляем узлы, которые не были достигнуты (изолированные)
                all_nodes = set()
                for package, deps in self.dependency_graph.items():
                    all_nodes.add(package)
                    all_nodes.update(deps)
                
                for node in all_nodes:
                    if node not in levels:
                        max_level = max(levels.values()) if levels else 0
                        levels[node] = max_level + 1
                        level_nodes[max_level + 1].append(node)
                
                return levels
            
            levels = calculate_levels()
            
            # Вычисляем позиции для каждого узла с автоматическим масштабированием
            canvas_width = 2000  # Базовая ширина
            canvas_height = max(1500, len(level_nodes) * level_height + 200)  # Автоматическая высота
            x_start = 100
            y_start = 100
            
            max_nodes_in_level = max(len(nodes) for nodes in level_nodes.values()) if level_nodes else 1
            horizontal_spacing = min(200, canvas_width // max(1, max_nodes_in_level))
            
            for level in sorted(level_nodes.keys()):
                nodes_in_level = level_nodes[level]
                level_y = y_start + level * level_height
                
                # Равномерно распределяем узлы по ширине
                if len(nodes_in_level) == 1:
                    x_positions = [canvas_width // 2]
                else:
                    total_level_width = len(nodes_in_level) * horizontal_spacing
                    start_x = max(x_start, (canvas_width - total_level_width) // 2)
                    x_positions = [start_x + i * horizontal_spacing for i in range(len(nodes_in_level))]
                
                for i, node in enumerate(nodes_in_level):
                    positions[node] = (x_positions[i], level_y)
            
            # Устанавливаем область прокрутки
            canvas.configure(scrollregion=(0, 0, canvas_width, canvas_height))
            
            # Рисуем связи СНАЧАЛА (чтобы они были под узлами)
            for package, dependencies in self.dependency_graph.items():
                if package in positions:
                    x1, y1 = positions[package]
                    for dep in dependencies:
                        if dep in positions:
                            x2, y2 = positions[dep]
                            # Рисуем стрелку от пакета к зависимости
                            canvas.create_line(x1, y1 + node_height/2, x2, y2 - node_height/2, 
                                            arrow=tk.LAST, arrowshape=(8, 10, 5), width=1, fill="gray")
            
            # Рисуем узлы ПОСЛЕ связей (чтобы они были сверху)
            for node, (x, y) in positions.items():
                # Основной пакет - другой цвет
                if node == self.config['package_name']:
                    color = "#4A90E2"  # Синий
                    border_color = "#2C5AA0"
                else:
                    color = "#50C878"  # Зеленый
                    border_color = "#2E8B57"
                
                # Рисуем прямоугольник со скругленными углами (эмулируем)
                canvas.create_rectangle(x - node_width/2, y - node_height/2, 
                                      x + node_width/2, y + node_height/2,
                                      fill=color, outline=border_color, width=2,
                                      tags="node")
                
                # Добавляем текст (обрезаем если слишком длинный)
                display_text = node
                if len(node) > 20:
                    # Пытаемся разбить по частям
                    parts = node.split(':')
                    if len(parts) == 2:
                        display_text = f"{parts[0][:15]}...\n{parts[1]}"
                    else:
                        display_text = node[:17] + "..."
                
                canvas.create_text(x, y, text=display_text, font=("Arial", font_size), 
                                 width=node_width-10, tags="node_text")
            
            # Добавляем легенду
            legend_x = 50
            legend_y = 30
            
            canvas.create_rectangle(legend_x, legend_y, legend_x + 20, legend_y + 20, 
                                  fill="#4A90E2", outline="#2C5AA0", width=1)
            canvas.create_text(legend_x + 30, legend_y + 10, text="Основной пакет", 
                             anchor="w", font=("Arial", 9, "bold"))
            
            canvas.create_rectangle(legend_x + 150, legend_y, legend_x + 170, legend_y + 20, 
                                  fill="#50C878", outline="#2E8B57", width=1)
            canvas.create_text(legend_x + 180, legend_y + 10, text="Зависимости", 
                             anchor="w", font=("Arial", 9, "bold"))
            
            # Добавляем информацию о графе
            info_text = f"Всего узлов: {len(positions)} | Всего связей: {sum(len(deps) for deps in self.dependency_graph.values())}"
            canvas.create_text(canvas_width // 2, 30, text=info_text, 
                             font=("Arial", 10, "bold"), fill="#333333")
            
            # Добавляем заголовок
            title_text = f"Граф зависимостей: {self.config['package_name']}"
            canvas.create_text(canvas_width // 2, 70, text=title_text, 
                             font=("Arial", 12, "bold"), fill="#000000")
            
            # Добавляем zoom функциональность
            def zoom(event):
                scale = 1.1 if event.delta > 0 else 0.9
                canvas.scale("all", event.x, event.y, scale, scale)
            
            canvas.bind("<MouseWheel>", zoom)
            
            root.mainloop()
            
        except Exception as e:
            print(f"Ошибка при создании графического представления: {e}")

    def run(self):
        """Основной метод запуска приложения"""
        try:
            
            config = self.load_config()
            self.validate_config(config)
            self.config = config
            
            # Особенности тестового режима
            if config['test_mode'] and not config['repository_url'].startswith(('http://', 'https://')):
                print(f"\nРЕЖИМ: Тестовый репозиторий из файла")
                print(f"Файл: {config['repository_url']}")
                self.load_test_repository()
            elif config['test_mode']:
                print(f"\nРЕЖИМ: Тестовые данные (встроенные)")
            else:
                print(f"\nРЕЖИМ: Реальный Maven репозиторий")
            
            print(f"\nПОСТРОЕНИЕ ГРАФА ЗАВИСИМОСТЕЙ:")
            dependency_graph = self.build_dependency_graph()
            
            # ASCII дерево (если включено в конфиге)
            if self.config['ascii_tree'] and dependency_graph:
                self.print_dependency_tree(dependency_graph)
            elif not dependency_graph:
                print("Граф зависимостей пуст")
            
            # Генерация Mermaid представления
            mermaid_code = self.generate_mermaid_graph()
            
            # Сохраняем код в файл .mmd
            mermaid_filename = f"mermaid_{self.config['package_name'].replace(':', '_')}.mmd"
            with open(mermaid_filename, 'w') as f:
                f.write(mermaid_code)
            print(f"\nMermaid код сохранен в файл: {mermaid_filename}")
            
            # Создаем графическое представление с помощью tkinter
            self.create_tkinter_graph()
            
            
        except KeyboardInterrupt:
            print("\nПрограмма прервана пользователем")
            sys.exit(1)
        except Exception as e:
            print(f"\nОШИБКА: {e}")
            sys.exit(1)

def main():
    analyzer = MavenDependencyAnalyzer({})
    analyzer.run()

if __name__ == "__main__":
    main()

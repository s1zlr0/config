Этап 5. Визуализация
1. Общее описание.
Пятый этап представляет систему визуализации графов зависимостей. Реализованы текстовое представление графа зависимостей на языке
диаграмм Mermaid, интерактивная визуализация с использованием Tkinter, а также ASCII-деревья для консольного вывода.
2. Описание всех функций и настроек.

## Параметры командной строки:

| Параметр | Описание |
|----------|-----------|
| `--package` | **Обязательный**. Имя анализируемого Maven пакета в формате groupId:artifactId |
| `--repository` | **Обязательный**. URL Maven репозитория или путь к файлу с тестовым графом |
| `--repo-mode` | Режим работы: "local" или "remote" (по умолчанию: "remote") |
| `--version` | Версия пакета в формате X.Y.Z или "latest" (по умолчанию: "latest") |
| `--output` | Формат вывода: "ascii", "mermaid", "gui" или "all" (по умолчанию: "all") |
| `--depth` | Максимальная глубина анализа (по умолчанию: 2) |
| `--ascii` | **Флаг**. Вывод зависимостей в виде ASCII-дерева |
| `--examples` | **Флаг**. Демонстрация примеров для трёх пакетов |
| `--compare-maven` | **Флаг**. Сравнение с нативными инструментами Maven |

## Внутренние функции:

| Функция | Описание |
|---------|-----------|
| `validate_package_name()` | Проверяет корректность имени пакета (формат groupId:artifactId) |
| `validate_repository()` | Проверяет URL репозитория или существование локального файла |
| `validate_version()` | Проверяет формат версии (X.Y.Z или "latest") |
| `validate_output_format()` | Проверяет допустимые форматы вывода (ascii, mermaid, gui, all) |
| `validate_depth()` | Проверяет, что глубина - положительное число в диапазоне 1-10 |
| `get_package_dependencies()` | Извлекает зависимости пакета из Maven репозитория |
| `get_latest_version()` | Получает последнюю версию пакета из Maven metadata |
| `load_test_repository()` | Загружает тестовый граф из YAML файла формата A: [B, C] |
| `build_dependency_graph()` | Строит граф зависимостей с ограничением глубины (BFS алгоритм) |
| `generate_mermaid_graph()` | Генерирует Mermaid-диаграмму из графа зависимостей |
| `create_tkinter_graph()` | Создает графическое представление графа с помощью Tkinter |
| `print_ascii_tree()` | Выводит ASCII-дерево зависимостей в консоль |
| `detect_cycles()` | Обнаруживает циклические зависимости в графе (DFS алгоритм) |
| `get_load_order()` | Вычисляет порядок загрузки зависимостей (топологическая сортировка) |
| `compare_with_maven()` | Сравнивает результаты с нативными инструментами Maven |
| `demonstrate_examples()` | Демонстрирует визуализацию для трёх различных пакетов |

## Детальное описание функций:

### Валидационные функции
- **`validate_package_name()`**: Проверяет формат "groupId:artifactId", отсутствие пустых значений
- **`validate_repository()`**: Для remote режима проверяет валидность URL, для local - существование файла
- **`validate_version()`**: Поддерживает форматы "X.Y.Z", "X.Y", "X" и "latest"
- **`validate_output_format()`**: Обеспечивает корректность выбранного формата визуализации
- **`validate_depth()`**: Ограничивает глубину анализа для предотвращения бесконечных циклов

### Функции работы с данными
- **`get_package_dependencies()`**: Парсит POM файлы из Maven репозитория, извлекает зависимости
- **`get_latest_version()`**: Анализирует maven-metadata.xml для определения последней версии
- **`load_test_repository()`**: Загружает YAML файлы с тестовыми графами, валидирует структуру
- **`build_dependency_graph()`**: Реализует BFS с отслеживанием глубины и обработкой циклов

### Функции визуализации
- **`generate_mermaid_graph()`**: Создает текстовое представление для Mermaid JS с экранированием спецсимволов
- **`create_tkinter_graph()`**: Строит интерактивный граф с масштабированием, цветовым кодированием
- **`print_ascii_tree()`**: Форматирует древовидный вывод с Unicode символами и обозначением циклов

### Аналитические функции
- **`detect_cycles()`**: Использует модифицированный DFS для обнаружения циклических зависимостей
- **`get_load_order()`**: Реализует алгоритм Кана для топологической сортировки графа
- **`compare_with_maven()`**: Генерирует команды Maven для сравнения и анализирует расхождения

3. Описание команд для сборки проекта и запуска тестов.
Базовый запуск с конфигурационным файлом
python config2.5.py
Конфигурационный файл config.yaml
package_name: "com.fasterxml.jackson.core:jackson-databind"
repository_url: "https://repo1.maven.org/maven2"
test_mode: false
ascii_tree: true
max_depth: 2
4. Примеры использования.
Пакет jackson
<img width="2744" height="907" alt="image" src="https://github.com/user-attachments/assets/e285c04c-0669-4fe5-9706-d2f5991349a7" />

<img width="1574" height="1150" alt="image" src="https://github.com/user-attachments/assets/fd3c0eea-1701-4ea2-b411-74cfb7fe135d" />

Пакет commons
<img width="2661" height="674" alt="image" src="https://github.com/user-attachments/assets/e8c03d78-741c-49fd-a76c-74154e311fdb" />

<img width="1665" height="1180" alt="image" src="https://github.com/user-attachments/assets/d5fa3de5-c883-4f69-82b8-c815681e3761" />

Пакет spring-core
<img width="2664" height="826" alt="image" src="https://github.com/user-attachments/assets/49d3231d-f26b-4d0b-a4e8-9ee39b4c6d2b" />

<img width="1383" height="1174" alt="image" src="https://github.com/user-attachments/assets/a17756de-f487-42cf-a6f6-0a9d6b1f895c" />

Тестовый файл
<img width="2592" height="1028" alt="image" src="https://github.com/user-attachments/assets/b1b40093-c7bb-4733-8b7f-226d528eef8c" />

<img width="413" height="1056" alt="image" src="https://github.com/user-attachments/assets/ac41abe0-81f8-450c-b1a1-e2df71327171" />

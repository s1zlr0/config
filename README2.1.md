Этап 1. Минимальный прототип с конфигурацией
1. Общее описание.
Создано базовое CLI-приложение с поддержкой конфигурации через YAML-файл. Приложение читает настройки анализируемого пакета, URL репозитория,режимы работы и глубины анализа.
Реализована полная валидация всех параметров конфигурации с обработкой ошибок. При запуске программа выводит все текущие настройки в формате ключ-значение.
2. Примеры использования.
Стандартный запуск

<img width="876" height="219" alt="image" src="https://github.com/user-attachments/assets/61f05f42-70ea-4be4-9fb7-e0ae569a0fc4" />
Ошибка - отсутствует файл

<img width="547" height="49" alt="image" src="https://github.com/user-attachments/assets/b66bc366-1588-44ef-8805-7cc4153092e4" />
Ошибка - пустой файл

<img width="405" height="37" alt="image" src="https://github.com/user-attachments/assets/a7de1843-0b4b-4ee1-a818-4fa9c9c376cb" />
Ошибка - отсутствует поле

<img width="765" height="44" alt="image" src="https://github.com/user-attachments/assets/1737b4ca-7959-4a3d-83ac-5e126622971f" />
Ошибка - неверный тип данных

<img width="916" height="40" alt="image" src="https://github.com/user-attachments/assets/3ecc69eb-3d94-4640-9c41-058a453ee4b7" />

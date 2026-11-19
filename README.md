[![Online Boutique QA Tests](https://github.com/ilyhay/online-boutique-qa/actions/workflows/test.yml/badge.svg)](https://github.com/ilyhay/online-boutique-qa/actions/workflows/test.yml)

# Фреймворк автоматизированного тестирования для микросервисов Online Boutique

Комплексный фреймворк автоматизированного тестирования для микросервисного приложения [Online Boutique](https://github.com/GoogleCloudPlatform/microservices-demo) от Google.

## О проекте

Фреймворк покрывает 5 типов тестирования для распределенной системы из 11 gRPC-микросервисов, развернутых в Kubernetes:

| Тип тестирования | Описание | Количество тестов |
|------------------|----------|-------------------|
| Contract | Валидация gRPC API контрактов и структуры ответов | 1 |
| Integration | Сквозные бизнес-процессы (добавление товара в корзину) | 4 |
| Chaos | Отказоустойчивость, проверка механизма Self-healing и сохранности данных | 5 |
| Observability | Валидация логов микросервисов на отсутствие критических ошибок | 5 |
| Infrastructure | Проверка Kubernetes манифестов на соответствие best practices | 6 |

Итого: 21 автоматизированный тест.

## Технологический стек

- Python 3.12, pytest
- gRPC (с генерацией клиентского кода из .proto файлов)
- Официальный Kubernetes Python Client (без использования subprocess для управления кластером)
- Docker (для упаковки тестового окружения)
- GitHub Actions (CI/CD пайплайн)

## Структура проекта

```text
.
├── .github/workflows/     # Конфигурация CI/CD пайплайна
├── protos/                # gRPC контракты (.proto файлы)
├── generated/             # Сгенерированный Python-код (игнорируется в git)
├── tests/
│   ├── contract/          # Контрактные тесты gRPC API
│   ├── integration/       # Интеграционные тесты (E2E сценарии)
│   ├── chaos/             # Chaos Engineering тесты
│   ├── observability/     # Тесты валидации логов
│   └── infra/             # Тесты Kubernetes манифестов
├── Dockerfile             # Инструкции для сборки образа с тестами
├── requirements.txt       # Зависимости Python
└── README.md              # Документация проекта
```

## Быстрый старт

### Предварительные требования

- Python 3.12 или выше
- Установленный и запущенный кластер Kubernetes (Minikube или аналог)
- Утилита kubectl, настроенная на целевой кластер
- Развернутое приложение Online Boutique в кластере

### Локальный запуск тестов

1. Клонируйте репозиторий и активируйте виртуальное окружение:
   ```bash
   git clone <url-репозитория>
   cd online-boutique-qa
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Сгенерируйте Python-код из gRPC контракта:
   ```bash
   python3 -m grpc_tools.protoc \
     -I./protos \
     --python_out=./generated \
     --grpc_python_out=./generated \
     ./protos/demo.proto
   ```

3. Запустите полный набор тестов:
   ```bash
   pytest tests/ -v -s
   ```

4. Для запуска тестов по категориям:
   ```bash
   pytest tests/contract/ -v -s
   pytest tests/integration/ -v -s
   pytest tests/chaos/ -v -s
   pytest tests/observability/ -v -s
   pytest tests/infra/ -v -s
   ```

## Ключевые особенности реализации

### Chaos Engineering
Тест намеренно удаляет под cartservice через Kubernetes API и проверяет:
- Автоматическое создание нового пода с использованием Watch API.
- Восстановление доступности сервиса через gRPC после обновления правил маршрутизации kube-proxy.
- Сохранность данных в Redis после перезапуска пода.

### Infrastructure as Code Testing
Автоматическая статическая проверка Kubernetes манифестов на:
- Наличие resource limits и requests у всех контейнеров.
- Настройку livenessProbe и readinessProbe.
- Отсутствие тега :latest в образах контейнеров.
- Корректность селекторов у сервисов.

### Observability
Валидация логов работающих подов на:
- Отсутствие критических ошибок (panic, fatal, OOM, segmentation fault).
- Соответствие формату структурированных логов.
- Наличие записей оsuccessful обработке запросов.

## CI/CD Пайплайн

Проект настроен на автоматический запуск проверок в GitHub Actions при каждом push в основную ветку:
1. Code Quality Check: линтинг кода (flake8) и проверка форматирования (black).
2. Infrastructure Tests: запуск тестов манифестов на чистом окружении Ubuntu.
3. gRPC Code Generation Check: валидация корректности proto-файлов и процесса генерации кода.

Полный прогон интеграционных тестов в Kubernetes настроен на ручной запуск (workflow_dispatch) и требует наличия настроенного кластера с доступом через секреты CI/CD.

## Отчётность

Все тесты интегрированы с Allure Report. Пример отчёта:

![Allure Report](docs/allure-screenshot.png)

Полный интерактивный отчёт последнего CI-прогона доступен по ссылке:
https://ilyhay.github.io/online-boutique-qa/allure-report/

Локальная генерация отчёта:
```bash
pytest tests/ -v --alluredir=allure-results
allure generate allure-results -o allure-report --clean
allure open --host 0.0.0.0 --port 8080 allure-report
```

## Результаты по проекту

Разработала комплексный фреймворк автоматизированного тестирования для микросервисного приложения из 11 gRPC-сервисов в Kubernetes. Реализовала контрактные, интеграционные, Chaos Engineering и observability тесты с использованием официального Kubernetes Python Client. Настроила CI/CD пайплайн в GitHub Actions для автоматической валидации кода и инфраструктуры.

# 🧪 Online Boutique QA Test Suite

Комплексный фреймворк автоматизированного тестирования для микросервисного приложения [Online Boutique](https://github.com/GoogleCloudPlatform/microservices-demo) от Google.

## 📋 О проекте

Фреймворк покрывает 5 типов тестирования для распределенной системы из 11 gRPC-микросервисов в Kubernetes:

| Тип тестов | Описание | Кол-во тестов |
|------------|----------|---------------|
| **Contract** | Валидация gRPC API контрактов | 1 |
| **Integration** | Сквозные бизнес-процессы (добавление в корзину) | 4 |
| **Chaos** | Отказоустойчивость и Self-healing | 5 |
| **Observability** | Валидация логов микросервисов | 5 |
| **Infrastructure** | Проверка K8s манифестов на best practices | 6 |

**Всего: 21 автотест**

## 🛠️ Технологический стек

- **Python 3.12** + **pytest**
- **gRPC** (с генерацией кода из `.proto` файлов)
- **Kubernetes Python Client** (официальный, без subprocess-костылей)
- **Docker** (для упаковки тестов)
- **GitHub Actions** (CI/CD)

## 🚀 Быстрый старт

### Предварительные требования

- Python 3.12+
- Minikube (или любой K8s кластер)
- kubectl
- Online Boutique развернут в кластере

### Локальный запуск

```bash
# 1. Клонируем и устанавливаем зависимости
git clone <your-repo-url>
cd online-boutique-tests
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Генерируем gRPC код из proto-файла
python -m grpc_tools.protoc \
  -I./protos \
  --python_out=./generated \
  --grpc_python_out=./generated \
  ./protos/demo.proto

# 3. Запускаем все тесты
pytest tests/ -v -s

# Или запускаем по категориям:
pytest tests/contract/ -v -s
pytest tests/integration/ -v -s
pytest tests/chaos/ -v -s
pytest tests/observability/ -v -s
pytest tests/infra/ -v -s

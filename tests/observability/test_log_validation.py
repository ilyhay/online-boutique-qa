"""
Тест наблюдаемости: Проверка логов микросервисов

Этот тест проверяет, что микросервисы корректно пишут логи:
1. Логи содержат ожидаемые сообщения
2. В логах нет критических ошибок
3. Формат логов соответствует стандартам

Это важно для отладки и мониторинга в production.
"""
import pytest
import time
import grpc
import sys
import os
from kubernetes import client, config

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../generated')))
import demo_pb2
import demo_pb2_grpc

PRODUCT_CATALOG_PORT = 3550

@pytest.fixture(scope="module")
def k8s_client():
    """Инициализация Kubernetes клиент"""
    try:
        config.load_kube_config()
    except config.config_exception.ConfigException:
        pytest.skip("Не удалось загрузить kubeconfig")
    return client.CoreV1Api()


@pytest.fixture(scope="module")
def port_forward_product_catalog():
    """Запуск port-forward для productcatalogservice"""
    import subprocess
    print("Запуск port-forward для productcatalogservice...")
    process = subprocess.Popen(
        ["kubectl", "port-forward", "service/productcatalogservice", f"{PRODUCT_CATALOG_PORT}:3550"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(2)
    yield
    process.terminate()
    process.wait()


class TestLogValidation:
    """Тесты валидации логов микросервисов"""

    def test_01_make_request_to_generate_logs(self, port_forward_product_catalog):
        """Шаг 1: Создание запроса, чтобы сгенерировать логи"""
        print("Шаг 1: Создание запроса для генерации логов...")
        
        channel = grpc.insecure_channel(f'localhost:{PRODUCT_CATALOG_PORT}')
        stub = demo_pb2_grpc.ProductCatalogServiceStub(channel)
        
        for i in range(3):
            try:
                products = stub.ListProducts(demo_pb2.Empty(), timeout=5)
                print(f"Запрос {i+1}: получено {len(products.products)} товаров")
            except grpc.RpcError as e:
                pytest.fail(f"Запрос не удался: {e}")
        
        time.sleep(2)

    def test_02_check_logs_exist(self, k8s_client):
        """Шаг 2: Проверка, что логи вообще пишутся"""
        print("Шаг 2: Проверка наличия логов...")
        
        pods = k8s_client.list_namespaced_pod(
            namespace="default",
            label_selector="app=productcatalogservice"
        )
        
        running_pods = [p for p in pods.items if p.status.phase == "Running"]
        assert len(running_pods) > 0, "Нет работающих подов productcatalogservice"
        
        pod_name = running_pods[0].metadata.name
        
        logs = k8s_client.read_namespaced_pod_log(
            name=pod_name,
            namespace="default",
            tail_lines=50
        )
        
        assert logs, "Логи пусты"
        assert len(logs) > 0, "Логи не содержат данных"
        
        print(f"Логи найдены, размер: {len(logs)} символов")
        self.__class__.pod_name = pod_name
        self.__class__.logs = logs

    def test_03_check_log_format(self):
        """Шаг 3: Проверка формата логов"""
        print("Шаг 3: Проверка формата логов...")
        
        assert hasattr(self.__class__, 'logs'), "Предыдущий шаг не выполнен"
        logs = self.__class__.logs
        
        log_lines = [line for line in logs.split('\n') if line.strip()]
        assert len(log_lines) > 0, "Нет строк в логах"
        
        has_info_or_debug = any(
            'info' in line.lower() or 'debug' in line.lower() or 'INFO' in line or 'DEBUG' in line
            for line in log_lines
        )
        
        assert has_info_or_debug, "В логах не найдены записи уровня INFO или DEBUG"
        
        print(f"Формат логов корректен, найдено {len(log_lines)} строк")

    def test_04_check_no_critical_errors(self):
        """Шаг 4: Проверка отсутствия критических ошибок"""
        print("Шаг 4: Проверка отсутствия критических ошибок...")
        
        assert hasattr(self.__class__, 'logs'), "Предыдущий шаг не выполнен"
        logs = self.__class__.logs
        
        error_patterns = [
            'panic:',
            'fatal error',
            'stack trace',
            'segmentation fault',
            'out of memory'
        ]
        
        error_lines = []
        for line in logs.split('\n'):
            line_lower = line.lower()
            if any(pattern in line_lower for pattern in error_patterns):
                error_lines.append(line)
        
        if error_lines:
            print(f"Найдены критические ошибки:")
            for line in error_lines[:5]:
                print(f"     {line}")
            pytest.fail(f"Найдено {len(error_lines)} критических ошибок в логах")
        
        print(f"Критических ошибок не найдено")

    def test_05_check_for_request_logs(self):
        """Шаг 5: Проверка, что запросы логируются"""
        print("Шаг 5: Проверка логирования запросов...")
        
        assert hasattr(self.__class__, 'logs'), "Предыдущий шаг не выполнен"
        logs = self.__class__.logs
        
        request_indicators = [
            'ListProducts',
            'GET',
            'request',
            'method',
            'rpc'
        ]
        
        found_requests = []
        for line in logs.split('\n'):
            line_lower = line.lower()
            if any(indicator.lower() in line_lower for indicator in request_indicators):
                found_requests.append(line)
        
        assert len(found_requests) > 0, "В логах не найдены записи о запросах"
        
        print(f"Найдено {len(found_requests)} записей о запросах")
        if found_requests:
            print(f"Пример: {found_requests[0][:100]}...")


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])

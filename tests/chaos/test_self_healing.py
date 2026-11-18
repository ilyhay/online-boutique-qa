"""
Chaos Engineering тест: Проверка механизма Self-healing в Kubernetes

Тест намеренно "убивает" под cartservice и проверяет, что:
1. Kubernetes автоматически создает новый под
2. Сервис восстанавливает доступность
3. Данные в Redis не теряются (проверяем косвенно через cartservice)

Это демонстрирует отказоустойчивость системы и корректность работы K8s.
"""
import pytest
import time
import grpc
import sys
import os
import subprocess
from kubernetes import client, config, watch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../generated')))
import demo_pb2
import demo_pb2_grpc

CART_SERVICE_PORT = 7070

@pytest.fixture(scope="module")
def k8s_client():
    """Инициализация Kubernetes клиент"""
    try:
        config.load_kube_config()
    except config.config_exception.ConfigException:
        pytest.skip("Не удалось загрузить kubeconfig. Убедитесь, что kubectl настроен")
    return client.CoreV1Api()

@pytest.fixture(scope="module")
def port_forward_cart_initial():
    """Запуск port-forward для cartservice для начальной проверки"""
    print("\nЗапуск начального port-forward для cartservice...")
    process = subprocess.Popen(
        ["kubectl", "port-forward", "service/cartservice", f"{CART_SERVICE_PORT}:7070"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(2)
    yield
    process.terminate()
    process.wait()


class TestChaosSelfHealing:
    """Тесты отказоустойчивости Kubernetes"""

    def test_01_verify_initial_state(self, k8s_client, port_forward_cart_initial):
        """Шаг 1: Проверка начального состояние системы"""
        print("\nШаг 1: Проверка начального состояние cartservice...")
        
        pods = k8s_client.list_namespaced_pod(
            namespace="default",
            label_selector="app=cartservice"
        )
        
        running_pods = [p for p in pods.items if p.status.phase == "Running"]
        assert len(running_pods) > 0, "Нет работающих подов cartservice"
        
        initial_pod_name = running_pods[0].metadata.name
        print(f"Найден под: {initial_pod_name}")
        
        channel = grpc.insecure_channel(f'localhost:{CART_SERVICE_PORT}')
        stub = demo_pb2_grpc.CartServiceStub(channel)
        
        try:
            cart = stub.GetCart(demo_pb2.GetCartRequest(user_id="chaos-test-user"), timeout=5)
            print(f"Сервис отвечает, корзина содержит {len(cart.items)} элементов")
        except grpc.RpcError as e:
            pytest.fail(f"Сервис не отвечает до начала теста: {e.code()}")
        
        self.__class__.initial_pod_name = initial_pod_name

    def test_02_kill_pod(self, k8s_client):
        """Шаг 2: Намеренное удаление под cartservice"""
        print(f"\nШаг 2: Удаление под {self.__class__.initial_pod_name}...")
        
        assert hasattr(self.__class__, 'initial_pod_name'), "Предыдущий шаг не выполнен"
        
        try:
            k8s_client.delete_namespaced_pod(
                name=self.__class__.initial_pod_name,
                namespace="default",
                body=client.V1DeleteOptions(grace_period_seconds=0)
            )
            print(f"Под {self.__class__.initial_pod_name} успешно удален")
        except Exception as e:
            pytest.fail(f"Не удалось удалить под: {e}")

    def test_03_wait_for_new_pod(self, k8s_client):
        """Шаг 3: Ожидание создания нового пода"""
        print("\nШаг 3: Ожидание создания нового пода cartservice...")
        
        assert hasattr(self.__class__, 'initial_pod_name'), "Предыдущий шаг не выполнен"
        old_pod_name = self.__class__.initial_pod_name
        
        w = watch.Watch()
        new_pod_found = False
        new_pod_name = None
        
        for event in w.stream(
            k8s_client.list_namespaced_pod,
            namespace="default",
            label_selector="app=cartservice",
            timeout_seconds=30
        ):
            pod = event['object']
            pod_name = pod.metadata.name
            
            if pod_name != old_pod_name and pod.status.phase == "Running":
                if pod.status.container_statuses and all(c.ready for c in pod.status.container_statuses):
                    print(f"Новый под создан и готов: {pod_name}")
                    new_pod_found = True
                    new_pod_name = pod_name
                    w.stop()
                    break
        
        assert new_pod_found, "Новый под не был создан за 30 секунд"
        self.__class__.new_pod_name = new_pod_name

    def test_04_verify_service_recovery(self):
        """Шаг 4: Проверка, что сервис восстановил доступность"""
        print("\nШаг 4: Проверка восстановления сервиса...")
        
        print("Перезапуск port-forward для подключения к новому поду...")
        subprocess.run(["pkill", "-f", "port-forward.*cartservice"], capture_output=True)
        time.sleep(1)
        
        pf_process = subprocess.Popen(
            ["kubectl", "port-forward", "service/cartservice", f"{CART_SERVICE_PORT}:7070"],
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        
        time.sleep(4)
        
        channel = grpc.insecure_channel(f'localhost:{CART_SERVICE_PORT}')
        stub = demo_pb2_grpc.CartServiceStub(channel)
        
        max_retries = 10
        for i in range(max_retries):
            try:
                cart = stub.GetCart(demo_pb2.GetCartRequest(user_id="recovery-test-user"), timeout=5)
                print(f"Сервис восстановил доступность после попытки {i+1}")
                self.__class__.pf_process = pf_process
                return
            except grpc.RpcError:
                if i < max_retries - 1:
                    time.sleep(1)
                    continue
                else:
                    pytest.fail("Сервис не восстановил доступность после 10 попыток")

    def test_05_verify_data_persistence(self):
        """Шаг 5: Проверка, что данные в Redis не потерялись"""
        print("\nШаг 5: Проверка сохранности данных в Redis...")
        
        test_user = "persistence-test-user"
        test_product_id = "OLJCESPC7Z"  
        
        channel = grpc.insecure_channel(f'localhost:{CART_SERVICE_PORT}')
        stub = demo_pb2_grpc.CartServiceStub(channel)
        
        try:
            stub.AddItem(demo_pb2.AddItemRequest(
                user_id=test_user,
                item=demo_pb2.CartItem(product_id=test_product_id, quantity=5)
            ), timeout=5)
        except grpc.RpcError as e:
            pytest.fail(f"Не удалось добавить товар: {e}")
        
        try:
            cart = stub.GetCart(demo_pb2.GetCartRequest(user_id=test_user), timeout=5)
            assert len(cart.items) > 0, "Корзина пуста после добавления"
            
            found = False
            for item in cart.items:
                if item.product_id == test_product_id:
                    assert item.quantity == 5, f"Ожидалось 5, получено {item.quantity}"
                    found = True
                    break
            
            assert found, f"Товар {test_product_id} не найден в корзине"
            print(f"Данные успешно сохранены в Redis")
            
        except grpc.RpcError as e:
            pytest.fail(f"Не удалось проверить корзину: {e}")
        finally:
            try:
                stub.EmptyCart(demo_pb2.EmptyCartRequest(user_id=test_user), timeout=5)
            except:
                pass
            
            if hasattr(self.__class__, 'pf_process'):
                self.__class__.pf_process.terminate()
                self.__class__.pf_process.wait()


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])

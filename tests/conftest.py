import pytest
import subprocess
import time


@pytest.fixture(scope="session")
def check_minikube_running():
    """Проверка, что Minikube запущен перед началом тестов"""
    result = subprocess.run(["minikube", "status"], capture_output=True, text=True)
    if result.returncode != 0:
        pytest.skip("Minikube не запущен. Выполните 'minikube start'")


@pytest.fixture(scope="session")
def check_pods_running():
    """Проверка, что все поды Online Boutique в статусе Running"""
    result = subprocess.run(
        [
            "kubectl",
            "get",
            "pods",
            "-l",
            "app!=loadgenerator",
            "-o",
            "jsonpath={.items[*].status.phase}",
        ],
        capture_output=True,
        text=True,
    )
    phases = result.stdout.strip().split()
    if not all(p == "Running" for p in phases):
        pytest.skip(f"Не все поды в статусе Running: {phases}")


def start_port_forward(service_name, local_port, target_port):
    """Универсальная функция для запуска port-forward"""
    process = subprocess.Popen(
        [
            "kubectl",
            "port-forward",
            f"service/{service_name}",
            f"{local_port}:{target_port}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2)
    return process


@pytest.fixture(scope="module")
def port_forward_product_catalog():
    """Port-forward для productcatalogservice (gRPC порт 3550)"""
    print("Запуск port-forward для productcatalogservice...")
    process = start_port_forward("productcatalogservice", 3550, 3550)
    yield
    print("Остановка port-forward для productcatalogservice")
    process.terminate()
    process.wait()


@pytest.fixture(scope="module")
def port_forward_cart_service():
    """Port-forward для cartservice (gRPC порт 7070)"""
    print("Запуск port-forward для cartservice...")
    process = start_port_forward("cartservice", 7070, 7070)
    yield
    print("Остановка port-forward для cartservice")
    process.terminate()
    process.wait()

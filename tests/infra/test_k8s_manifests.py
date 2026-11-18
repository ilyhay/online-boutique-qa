import json
import os
import subprocess

import pytest
import yaml

MANIFESTS_DIR = os.path.expanduser("~/microservices-demo/kubernetes-manifests")


@pytest.fixture(scope="module")
def load_manifests():
    """Загружает все YAML манифесты"""
    manifests = []
    target_dir = MANIFESTS_DIR

    if not os.path.exists(target_dir):
        target_dir = os.path.join(os.getcwd(), "microservices-demo-ref", "kubernetes-manifests")

    if not os.path.exists(target_dir):
        pytest.skip(f"Директория с манифестами не найдена: {target_dir}")

    for filename in os.listdir(target_dir):
        if filename.endswith(".yaml") or filename.endswith(".yml"):
            filepath = os.path.join(target_dir, filename)
            with open(filepath, "r") as f:
                try:
                    docs = list(yaml.safe_load_all(f))
                    for doc in docs:
                        if doc:
                            manifests.append({"filename": filename, "content": doc})
                except yaml.YAMLError as e:
                    pytest.fail(f"Ошибка парсинга {filename}: {e}")
    return manifests


class TestK8sManifests:
    """Тесты валидации Kubernetes манифестов"""

    def test_01_manifests_exist(self, load_manifests):
        print("\nШаг 1: Проверка наличия манифестов...")
        assert len(load_manifests) > 0, "Не найдено ни одного манифеста"
        print(f"  Найдено {len(load_manifests)} манифестов")

    def test_02_deployments_have_resource_limits(self, load_manifests):
        print("\nШаг 2: Проверка resource limits...")
        deployments = [m for m in load_manifests if m["content"].get("kind") == "Deployment"]
        assert len(deployments) > 0, "Не найдено ни одного Deployment"
        issues = []
        for deployment in deployments:
            name = deployment["content"]["metadata"]["name"]
            spec = deployment["content"].get("spec", {})
            template = spec.get("template", {})
            pod_spec = template.get("spec", {})
            containers = pod_spec.get("containers", [])
            for container in containers:
                container_name = container.get("name", "unknown")
                resources = container.get("resources", {})
                if not resources.get("limits"):
                    issues.append(f"{name}/{container_name}: отсутствуют limits")
                if not resources.get("requests"):
                    issues.append(f"{name}/{container_name}: отсутствуют requests")
        if issues:
            print("  Найдены проблемы:")
            for issue in issues:
                print(f"     - {issue}")
            pytest.fail(f"У {len(issues)} контейнеров отсутствуют resource limits/requests")
        print(f"  Все {len(deployments)} Deployment имеют resource limits/requests")

    def test_03_deployments_have_probes(self, load_manifests):
        print("\nШаг 3: Проверка health probes...")
        deployments = [m for m in load_manifests if m["content"].get("kind") == "Deployment"]
        issues = []
        for deployment in deployments:
            name = deployment["content"]["metadata"]["name"]
            if name == "loadgenerator":
                continue
            spec = deployment["content"].get("spec", {})
            template = spec.get("template", {})
            pod_spec = template.get("spec", {})
            containers = pod_spec.get("containers", [])
            for container in containers:
                container_name = container.get("name", "unknown")
                if not container.get("livenessProbe"):
                    issues.append(f"{name}/{container_name}: отсутствует livenessProbe")
                if not container.get("readinessProbe"):
                    issues.append(f"{name}/{container_name}: отсутствует readinessProbe")
        if issues:
            print("  Найдены проблемы:")
            for issue in issues:
                print(f"     - {issue}")
            pytest.fail(f"У {len(issues)} контейнеров отсутствуют health probes")
        print("  Все критические Deployment имеют liveness и readiness probes")

    def test_04_services_have_selectors(self, load_manifests):
        print("\nШаг 4: Проверка Service selectors...")
        services = [m for m in load_manifests if m["content"].get("kind") == "Service"]
        issues = []
        for service in services:
            name = service["content"]["metadata"]["name"]
            spec = service["content"].get("spec", {})
            if not spec.get("selector"):
                issues.append(f"{name}: отсутствует selector")
        if issues:
            print("  Найдены проблемы:")
            for issue in issues:
                print(f"     - {issue}")
            pytest.fail(f"У {len(issues)} Services отсутствуют selectors")
        print(f"  Все {len(services)} Services имеют selectors")

    def test_05_no_latest_tags(self, load_manifests):
        print("\nШаг 5: Проверка отсутствия явного тега :latest...")
        deployments = [m for m in load_manifests if m["content"].get("kind") == "Deployment"]
        issues = []
        for deployment in deployments:
            name = deployment["content"]["metadata"]["name"]
            spec = deployment["content"].get("spec", {})
            template = spec.get("template", {})
            pod_spec = template.get("spec", {})
            containers = pod_spec.get("containers", [])
            for container in containers:
                image = container.get("image", "")
                if ":latest" in image:
                    issues.append(f"{name}: явный :latest в образе {image}")
        if issues:
            print("  Найдены проблемы:")
            for issue in issues:
                print(f"     - {issue}")
            pytest.fail(f"Найдено {len(issues)} образов с явным тегом :latest")
        print("  Явных :latest не найдено (полные теги или placeholders для сборки)")

    def test_06_check_running_pods_match_manifests(self):
        print("\nШаг 6: Проверка соответствия запущенных подов...")
        result = subprocess.run(
            ["kubectl", "get", "pods", "-o", "json"], capture_output=True, text=True
        )
        if result.returncode != 0:
            pytest.skip("Не удалось получить список подов")
        pods_data = json.loads(result.stdout)
        running_pods = [p for p in pods_data["items"] if p["status"]["phase"] == "Running"]
        expected_services = [
            "frontend",
            "cartservice",
            "productcatalogservice",
            "checkoutservice",
            "currencyservice",
            "paymentservice",
        ]
        found_services = set()
        for pod in running_pods:
            labels = pod["metadata"].get("labels", {})
            app_name = labels.get("app", "")
            if app_name in expected_services:
                found_services.add(app_name)
        missing = set(expected_services) - found_services
        if missing:
            pytest.fail(f"Не найдены запущенные поды для сервисов: {missing}")
        print(f"  Все {len(expected_services)} основных сервисов запущены")

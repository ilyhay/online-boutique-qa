"""
Тест инфраструктуры: Проверка K8s манифестов на best practices

Этот тест проверяет, что Kubernetes манифесты написаны правильно:
1. У всех подов есть resource limits/requests
2. Настроены liveness и readiness probes
3. Соблюдены security best practices

Это важно для стабильности и безопасности production-системы.
"""
import pytest
import subprocess
import yaml
import os

MANIFESTS_DIR = os.path.expanduser("~/microservices-demo/kubernetes-manifests")

@pytest.fixture(scope="module")
def load_manifests():
    """Загружает все YAML манифесты"""
    manifests = []
    for filename in os.listdir(MANIFESTS_DIR):
        if filename.endswith('.yaml') or filename.endswith('.yml'):
            filepath = os.path.join(MANIFESTS_DIR, filename)
            with open(filepath, 'r') as f:
                try:
                    docs = list(yaml.safe_load_all(f))
                    for doc in docs:
                        if doc:
                            manifests.append({'filename': filename, 'content': doc})
                except yaml.YAMLError as e:
                    pytest.fail(f"Ошибка парсинга {filename}: {e}")
    return manifests

class TestK8sManifests:
    """Тесты валидации Kubernetes манифестов"""

    def test_01_manifests_exist(self, load_manifests):
        """Шаг 1: Проверка, что манифесты существуют"""
        print("Шаг 1: Проверка наличия манифестов...")
        
        assert len(load_manifests) > 0, "Не найдено ни одного манифеста"
        print(f"Найдено {len(load_manifests)} манифестов")

    def test_02_deployments_have_resource_limits(self, load_manifests):
        """Шаг 2: Проверка наличия resource limits у всех Deployments"""
        print("Шаг 2: Проверка resource limits...")
        
        deployments = [m for m in load_manifests if m['content'].get('kind') == 'Deployment']
        
        assert len(deployments) > 0, "Не найдено ни одного Deployment"
        
        issues = []
        for deployment in deployments:
            name = deployment['content']['metadata']['name']
            spec = deployment['content'].get('spec', {})
            template = spec.get('template', {})
            pod_spec = template.get('spec', {})
            containers = pod_spec.get('containers', [])
            
            for container in containers:
                container_name = container.get('name', 'unknown')
                resources = container.get('resources', {})
                
                if not resources.get('limits'):
                    issues.append(f"{name}/{container_name}: отсутствуют limits")
                if not resources.get('requests'):
                    issues.append(f"{name}/{container_name}: отсутствуют requests")
        
        if issues:
            print(f"Найдены проблемы:")
            for issue in issues:
                print(f"     - {issue}")
            pytest.fail(f"У {len(issues)} контейнеров отсутствуют resource limits/requests")
        
        print(f"Все {len(deployments)} Deployment имеют resource limits/requests")

    def test_03_deployments_have_probes(self, load_manifests):
        """Шаг 3: Проверка наличия liveness и readiness probes"""
        print("Шаг 3: Проверка health probes...")
        
        deployments = [m for m in load_manifests if m['content'].get('kind') == 'Deployment']
        
        issues = []
        for deployment in deployments:
            name = deployment['content']['metadata']['name']
            
            if name == 'loadgenerator':
                continue
            
            spec = deployment['content'].get('spec', {})
            template = spec.get('template', {})
            pod_spec = template.get('spec', {})
            containers = pod_spec.get('containers', [])
            
            for container in containers:
                container_name = container.get('name', 'unknown')
                
                if not container.get('livenessProbe'):
                    issues.append(f"{name}/{container_name}: отсутствует livenessProbe")
                if not container.get('readinessProbe'):
                    issues.append(f"{name}/{container_name}: отсутствует readinessProbe")
        
        if issues:
            print(f"Найдены проблемы:")
            for issue in issues:
                print(f"     - {issue}")
            pytest.fail(f"У {len(issues)} контейнеров отсутствуют health probes")
        
        print(f"Все критические Deployment имеют liveness и readiness probes")

    def test_04_services_have_selectors(self, load_manifests):
        """Шаг 4: Проверка, что у всех Services есть selectors"""
        print("Шаг 4: Проверка Service selectors...")
        
        services = [m for m in load_manifests if m['content'].get('kind') == 'Service']
        
        issues = []
        for service in services:
            name = service['content']['metadata']['name']
            spec = service['content'].get('spec', {})
            
            if not spec.get('selector'):
                issues.append(f"{name}: отсутствует selector")
        
        if issues:
            print(f"Найдены проблемы:")
            for issue in issues:
                print(f"     - {issue}")
            pytest.fail(f"У {len(issues)} Services отсутствуют selectors")
        
        print(f"Все {len(services)} Services имеют selectors")

    def test_05_no_latest_tags(self, load_manifests):
        """Шаг 5: Проверка, что не используются образы с тегом :latest"""
        print("Шаг 5: Проверка отсутствия тега :latest...")
        
        deployments = [m for m in load_manifests if m['content'].get('kind') == 'Deployment']
        
        issues = []
        for deployment in deployments:
            name = deployment['content']['metadata']['name']
            spec = deployment['content'].get('spec', {})
            template = spec.get('template', {})
            pod_spec = template.get('spec', {})
            containers = pod_spec.get('containers', [])
            
            for container in containers:
                image = container.get('image', '')
                if ':latest' in image or ':' not in image:
                    issues.append(f"{name}: образ {image} использует :latest или не имеет тега")
        
        if issues:
            print(f"Найдены проблемы:")
            for issue in issues:
                print(f"     - {issue}")
            pytest.fail(f"Найдено {len(issues)} образов с тегом :latest")
        
        print(f"Все образы имеют конкретные версии (не :latest)")

    def test_06_check_running_pods_match_manifests(self):
        """Шаг 6: Проверка, что запущенные поды соответствуют манифестам"""
        print("Шаг 6: Проверка соответствия запущенных подов...")
        
        result = subprocess.run(
            ["kubectl", "get", "pods", "-o", "json"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            pytest.skip("Не удалось получить список подов")
        
        import json
        pods_data = json.loads(result.stdout)
        
        running_pods = [
            p for p in pods_data['items']
            if p['status']['phase'] == 'Running'
        ]
        
        expected_services = [
            'frontend', 'cartservice', 'productcatalogservice',
            'checkoutservice', 'currencyservice', 'paymentservice'
        ]
        
        found_services = set()
        for pod in running_pods:
            labels = pod['metadata'].get('labels', {})
            app_name = labels.get('app', '')
            if app_name in expected_services:
                found_services.add(app_name)
        
        missing = set(expected_services) - found_services
        if missing:
            pytest.fail(f"Не найдены запущенные поды для сервисов: {missing}")
        
        print(f"Все {len(expected_services)} основных сервисов запущены")


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])

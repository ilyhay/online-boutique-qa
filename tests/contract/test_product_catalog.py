"""
Контрактный тест для productcatalogservice

Проверяет, что сервис корректно отвечает на запрос ListProducts и возвращает данные в соответствии с gRPC-контрактом.
"""
import grpc
import pytest
import sys
import os
import allure

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../generated')))
import demo_pb2
import demo_pb2_grpc

LOCAL_PORT = 3550

@allure.feature("Product Catalog Service")
@allure.story("List Products")
@allure.title("Получение списка всех товаров")
@allure.severity(allure.severity_level.CRITICAL)
def test_list_products_via_grpc(port_forward_product_catalog):
    """Тест: проверяем, что сервис каталога возвращает список товаров"""
    
    with allure.step("Подключение к gRPC сервису"):
        channel = grpc.insecure_channel(f'localhost:{LOCAL_PORT}')
        stub = demo_pb2_grpc.ProductCatalogServiceStub(channel)
    
    with allure.step("Отправка запроса ListProducts"):
        request = demo_pb2.Empty()
        try:
            response = stub.ListProducts(request, timeout=5)
        except grpc.RpcError as e:
            allure.attach(
                f"Error Code: {e.code()}\nDetails: {e.details()}",
                name="gRPC Error",
                attachment_type=allure.attachment_type.TEXT
            )
            pytest.fail(f"gRPC вызов завершился с ошибкой: {e.code()} - {e.details()}")
    
    with allure.step("Валидация ответа"):
        assert response is not None, "Ответ от сервиса пустой"
        allure.attach(
            f"Total products: {len(response.products)}",
            name="Response Summary",
            attachment_type=allure.attachment_type.TEXT
        )
        assert len(response.products) > 0, "Список товаров пуст"
        
        first_product = response.products[0]
        assert first_product.id != "", "ID товара не должен быть пустым"
        assert first_product.name != "", "Название товара не должно быть пустым"
        
        allure.attach(
            f"ID: {first_product.id}\nName: {first_product.name}\n"
            f"Price: ${first_product.price_usd.units}.{first_product.price_usd.nanos//10000000}",
            name="First Product Example",
            attachment_type=allure.attachment_type.TEXT
        )
    
    print(f"\nТест пройден: Получено {len(response.products)} товаров.")
    print(f"   Пример товара: '{first_product.name}' (ID: {first_product.id}), "
          f"цена: ${first_product.price_usd.units}.{first_product.price_usd.nanos//10000000}")

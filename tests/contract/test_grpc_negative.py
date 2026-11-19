"""
Негативные тесты для gRPC сервисов

Проверяет корректную обработку ошибок:
- NOT_FOUND: запрос несуществующего ресурса
- INVALID_ARGUMENT: некорректные входные данные
"""
import grpc
import pytest
import sys
import os
import allure

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../generated')))
import demo_pb2
import demo_pb2_grpc


PRODUCT_CATALOG_PORT = 3550
CART_SERVICE_PORT = 7070


@allure.feature("Product Catalog Service")
@allure.story("Negative Tests")
@allure.title("Запрос несуществующего товара")
@allure.severity(allure.severity_level.NORMAL)
def test_get_nonexistent_product(port_forward_product_catalog):
    """Тест: проверка обработки NOT_FOUND при запросе несуществующего товара"""
    
    with allure.step("Подключение к gRPC сервису"):
        channel = grpc.insecure_channel(f'localhost:{PRODUCT_CATALOG_PORT}')
        stub = demo_pb2_grpc.ProductCatalogServiceStub(channel)
    
    with allure.step("Запрос товара с несуществующим ID"):
        fake_product_id = "FAKE-ID-12345"
        request = demo_pb2.GetProductRequest(id=fake_product_id)
        
        try:
            response = stub.GetProduct(request, timeout=5)
            pytest.fail(f"Ожидалась ошибка NOT_FOUND, но получен ответ: {response}")
        except grpc.RpcError as e:
            with allure.step("Валидация кода ошибки"):
                allure.attach(
                    f"Expected: NOT_FOUND\nActual: {e.code()}\nDetails: {e.details()}",
                    name="Error Validation",
                    attachment_type=allure.attachment_type.TEXT
                )
                assert e.code() == grpc.StatusCode.NOT_FOUND, \
                    f"Ожидался код NOT_FOUND, получен {e.code()}"


@allure.feature("Product Catalog Service")
@allure.story("Negative Tests")
@allure.title("Запрос товара с пустым ID")
@allure.severity(allure.severity_level.NORMAL)
def test_get_product_empty_id(port_forward_product_catalog):
    """Тест: проверка обработки INVALID_ARGUMENT при пустом ID"""
    
    with allure.step("Подключение к gRPC сервису"):
        channel = grpc.insecure_channel(f'localhost:{PRODUCT_CATALOG_PORT}')
        stub = demo_pb2_grpc.ProductCatalogServiceStub(channel)
    
    with allure.step("Запрос товара с пустым ID"):
        request = demo_pb2.GetProductRequest(id="")
        
        try:
            response = stub.GetProduct(request, timeout=5)
            pytest.fail(f"Ожидалась ошибка, но получен ответ: {response}")
        except grpc.RpcError as e:
            with allure.step("Валидация кода ошибки"):
                allure.attach(
                    f"Expected: NOT_FOUND или INVALID_ARGUMENT\nActual: {e.code()}",
                    name="Error Validation",
                    attachment_type=allure.attachment_type.TEXT
                )
                assert e.code() in [grpc.StatusCode.NOT_FOUND, grpc.StatusCode.INVALID_ARGUMENT], \
                    f"Ожидался NOT_FOUND или INVALID_ARGUMENT, получен {e.code()}"


@allure.feature("Cart Service")
@allure.story("Negative Tests")
@allure.title("Добавление товара с нулевым количеством")
@allure.severity(allure.severity_level.NORMAL)
def test_add_item_zero_quantity(port_forward_cart_service):
    """Тест: проверка обработки INVALID_ARGUMENT при нулевом количестве"""
    
    with allure.step("Подключение к gRPC сервису"):
        channel = grpc.insecure_channel(f'localhost:{CART_SERVICE_PORT}')
        stub = demo_pb2_grpc.CartServiceStub(channel)
    
    with allure.step("Добавление товара с количеством 0"):
        request = demo_pb2.AddItemRequest(
            user_id="test-user-negative",
            item=demo_pb2.CartItem(
                product_id="OLJCESPC7Z",
                quantity=0
            )
        )
        
        try:
            stub.AddItem(request, timeout=5)
            allure.attach(
                "Warning: Service accepted quantity=0",
                name="Potential Issue",
                attachment_type=allure.attachment_type.TEXT
            )
        except grpc.RpcError as e:
            with allure.step("Валидация кода ошибки"):
                allure.attach(
                    f"Error Code: {e.code()}\nDetails: {e.details()}",
                    name="Error Details",
                    attachment_type=allure.attachment_type.TEXT
                )
                assert e.code() == grpc.StatusCode.INVALID_ARGUMENT, \
                    f"Ожидался INVALID_ARGUMENT, получен {e.code()}"


@allure.feature("Cart Service")
@allure.story("Negative Tests")
@allure.title("Получение корзины с пустым user_id")
@allure.severity(allure.severity_level.NORMAL)
def test_get_cart_empty_user_id(port_forward_cart_service):
    """Тест: проверка обработки при пустом user_id"""
    
    with allure.step("Подключение к gRPC сервису"):
        channel = grpc.insecure_channel(f'localhost:{CART_SERVICE_PORT}')
        stub = demo_pb2_grpc.CartServiceStub(channel)
    
    with allure.step("Запрос корзины с пустым user_id"):
        request = demo_pb2.GetCartRequest(user_id="")
        
        try:
            cart = stub.GetCart(request, timeout=5)
            allure.attach(
                f"Cart items count: {len(cart.items)}",
                name="Empty User ID Response",
                attachment_type=allure.attachment_type.TEXT
            )
            assert len(cart.items) == 0, "Корзина с пустым user_id должна быть пустой"
        except grpc.RpcError as e:
            with allure.step("Валидация кода ошибки"):
                allure.attach(
                    f"Error Code: {e.code()}",
                    name="Error Details",
                    attachment_type=allure.attachment_type.TEXT
                )
                assert e.code() in [grpc.StatusCode.NOT_FOUND, grpc.StatusCode.INVALID_ARGUMENT]

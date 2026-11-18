"""
Интеграционный тест: Сценарий "Добавление товара в корзину"

Тест проверяет взаимодействие нескольких микросервисов:
1. productcatalogservice - проверка существования товара
2. cartservice - добавление товара в корзину
3. redis-cart - косвенная проверка через cartservice

Тест имитирует реальный бизнес-процесс пользователя.
"""
import grpc
import pytest
import uuid
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../generated')))
import demo_pb2
import demo_pb2_grpc

PRODUCT_CATALOG_PORT = 3550
CART_SERVICE_PORT = 7070

@pytest.fixture(scope="module")
def test_user_id():
    """Генерация уникального ID пользователя для теста"""
    return f"test-user-{uuid.uuid4().hex[:8]}"


class TestCheckoutFlow:
    """Класс для группировки интеграционных тестов с общим состоянием"""

    def test_step_1_product_exists(self, port_forward_product_catalog):
        """Шаг 1: Проверка, что товар с известным ID существует в каталоге"""
        print("Шаг 1: Проверка существования товара в каталоге...")
        
        channel = grpc.insecure_channel(f'localhost:{PRODUCT_CATALOG_PORT}')
        stub = demo_pb2_grpc.ProductCatalogServiceStub(channel)
        
        # OLJCESPC7Z - это ID товара "Binoculars" из стандартного каталога
        product_id = "OLJCESPC7Z"
        
        try:
            product = stub.GetProduct(demo_pb2.GetProductRequest(id=product_id), timeout=5)
        except grpc.RpcError as e:
            pytest.fail(f"Не удалось получить товар {product_id}: {e.code()} - {e.details()}")
        
        assert product.id == product_id, f"Ожидался ID {product_id}, получен {product.id}"
        assert product.name != "", "Название товара не должно быть пустым"
        assert product.price_usd.units > 0 or product.price_usd.nanos > 0, "Цена должна быть > 0"
        
        print(f"Товар найден: '{product.name}', цена: ${product.price_usd.units}.{product.price_usd.nanos//10000000}")
        
        self.__class__.tested_product = product

    def test_step_2_add_to_cart(self, port_forward_cart_service, test_user_id):
        """Шаг 2: Добавление товара в корзину пользователя"""
        print(f"Шаг 2: Добавление товара в корзину пользователя {test_user_id}...")
        
        assert hasattr(self.__class__, 'tested_product'), "Предыдущий шаг не выполнен"
        product = self.__class__.tested_product
        
        channel = grpc.insecure_channel(f'localhost:{CART_SERVICE_PORT}')
        stub = demo_pb2_grpc.CartServiceStub(channel)
        
        quantity = 2
        
        try:
            stub.AddItem(demo_pb2.AddItemRequest(
                user_id=test_user_id,
                item=demo_pb2.CartItem(
                    product_id=product.id,
                    quantity=quantity
                )
            ), timeout=5)
        except grpc.RpcError as e:
            pytest.fail(f"Не удалось добавить товар в корзину: {e.code()} - {e.details()}")
        
        print(f"Добавлено в корзину: товар: '{product.name}, количество: {quantity}' ")

    def test_step_3_verify_cart_contents(self, port_forward_cart_service, test_user_id):
        """Шаг 3: Проверка, что товар действительно сохранился в корзине"""
        print(f"Шаг 3: Проверка содержимого корзины пользователя {test_user_id}...")
        
        assert hasattr(self.__class__, 'tested_product'), "Предыдущий шаг не выполнен"
        product = self.__class__.tested_product
        
        channel = grpc.insecure_channel(f'localhost:{CART_SERVICE_PORT}')
        stub = demo_pb2_grpc.CartServiceStub(channel)
        
        try:
            cart = stub.GetCart(demo_pb2.GetCartRequest(user_id=test_user_id), timeout=5)
        except grpc.RpcError as e:
            pytest.fail(f"Не удалось получить корзину: {e.code()} - {e.details()}")
        
        assert len(cart.items) > 0, "Корзина пуста после добавления товара."
        
        found_item = None
        for item in cart.items:
            if item.product_id == product.id:
                found_item = item
                break
        
        assert found_item is not None, f"Товар {product.id} не найден в корзине."
        assert found_item.quantity == 2, f"Ожидалось количество 2, получено {found_item.quantity}"
        
        print(f"В корзине найдено: {len(cart.items)} товар(ов)")
        print(f"Товар '{product.name}' присутствует в количестве: {found_item.quantity}")

    def test_step_4_empty_cart(self, port_forward_cart_service, test_user_id):
        """Шаг 4 (Cleanup): Очистка корзины"""
        print(f"Шаг 4: Очистка корзины пользователя {test_user_id}...")
        
        channel = grpc.insecure_channel(f'localhost:{CART_SERVICE_PORT}')
        stub = demo_pb2_grpc.CartServiceStub(channel)
        
        try:
            stub.EmptyCart(demo_pb2.EmptyCartRequest(user_id=test_user_id), timeout=5)
        except grpc.RpcError as e:
            pytest.fail(f"Не удалось очистить корзину: {e.code()} - {e.details()}")
        
        cart = stub.GetCart(demo_pb2.GetCartRequest(user_id=test_user_id), timeout=5)
        assert len(cart.items) == 0, "Корзина не очистилась!"
        
        print(f"Корзина очищена.")


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])

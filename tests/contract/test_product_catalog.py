"""
Контрактный тест для productcatalogservice

Проверяет, что сервис корректно отвечает на запрос ListProducts и возвращает данные в соответствии с gRPC-контрактом.
"""

import grpc
import pytest
import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../generated"))
)
import demo_pb2
import demo_pb2_grpc

LOCAL_PORT = 3550


def test_list_products_via_grpc(port_forward_product_catalog):
    """Тест: Проверка, что сервис каталога возвращает список товаров"""
    channel = grpc.insecure_channel(f"localhost:{LOCAL_PORT}")
    stub = demo_pb2_grpc.ProductCatalogServiceStub(channel)

    request = demo_pb2.Empty()

    try:
        response = stub.ListProducts(request, timeout=5)
    except grpc.RpcError as e:
        pytest.fail(f"gRPC вызов завершился с ошибкой: {e.code()} - {e.details()}")

    assert response is not None, "Ответ от сервиса пустой"
    assert len(response.products) > 0, "Список товаров пуст"

    first_product = response.products[0]
    assert first_product.id != "", "ID товара не должен быть пустым"
    assert first_product.name != "", "Название товара не должно быть пустым"

    print(f"Тест пройден: Получено {len(response.products)} товаров.")
    print(
        f"Пример товара: '{first_product.name}' (ID: {first_product.id}), "
        f"цена: ${first_product.price_usd.units}.{first_product.price_usd.nanos// 10000000}"
    )

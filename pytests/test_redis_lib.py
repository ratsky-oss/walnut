import pytest
from pkg.redis_lib import RedisHandler
from pkg.config import Config



REDIS_CONNECTION_STRING = Config().redis_url 


@pytest.fixture
def redis_handler():
    return RedisHandler(REDIS_CONNECTION_STRING)


def test_send_and_delete_info_to_redis(redis_handler):
    db_number = 0
    key = "test_key"
    message = {"foo": "bar"}

    # Отправить информацию в Redis
    redis_handler.send_info_to_redis(db_number, key, message)
    connection = redis_handler.get_connection(db_number)
    assert connection.hgetall(key) == message

    # Удалить информацию из Redis
    redis_handler.del_info_into_redis(db_number, key)
    assert connection.hgetall(key) == {}


def test_send_error_to_redis(redis_handler):
    db_number = 0
    job_name = "test_job"
    timestamp = "2023-04-12T12:00:00Z"
    error = "Test error message"

    # Отправить ошибку в Redis
    redis_handler.send_error_to_redis(db_number, job_name, timestamp, error)
    connection = redis_handler.get_connection(db_number)
    key = len(connection.keys())  # Получить ключ, по которому была отправлена ошибка

    error_info = connection.hgetall(key)
    assert error_info["job_name"] == job_name
    assert error_info["timestamp"] == timestamp
    assert error_info["error"] == error

    # Удалить ошибку из Redis
    redis_handler.del_info_into_redis(db_number, key)
    assert connection.hgetall(key) == {}


def test_del_all_keys_into_redis(redis_handler):
    db_number = 0
    keys = ["test_key1", "test_key2", "test_key3"]
    message = {"foo": "bar"}

    # Отправить информацию в Redis для каждого ключа
    for key in keys:
        redis_handler.send_info_to_redis(db_number, key, message)

    # Удалить все ключи из Redis
    redis_handler.del_all_keys_into_redis(db_number)
    connection = redis_handler.get_connection(db_number)
    for key in keys:
        assert connection.hgetall(key) == {}


def test_get_values_from_redis(redis_handler):
    db_number = 0
    keys_list = ["test_key1", "test_key2", "test_key3"]
    field = "foo"
    message = {field: "bar"}

    # Отправить информацию в Redis для каждого ключа
    for key in keys_list:
        redis_handler.send_info_to_redis(db_number, key, message)

    # Получить значения по ключам и полю
    values = redis_handler.get_values_from_redis(db_number, keys_list, field)
    for key in keys_list:
        assert values[key] == message[field]

    # Удалить ключи из Redis после тестирования
    for key in keys_list:
        redis_handler.del_info_into_redis(db_number, key)


def test_get_redis_len(redis_handler):
    db_number = 0
    key_pattern = "test_key_*"
    keys_list = ["test_key_1", "test_key_2", "test_key_3"]
    message = {"foo": "bar"}

    # Отправить информацию в Redis для каждого ключа
    for key in keys_list:
        redis_handler.send_info_to_redis(db_number, key, message)

    # Получить количество ключей с заданным шаблоном
    keys_count = redis_handler.get_redis_len(db_number, key_pattern)
    assert keys_count == len(keys_list)

    # Удалить ключи из Redis после тестирования
    for key in keys_list:
        redis_handler.del_info_into_redis(db_number, key)

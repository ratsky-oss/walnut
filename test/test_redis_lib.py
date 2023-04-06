import pytest
from datetime import timedelta

from pkg.redis_lib import RedisHandler
from pkg.config import WorkerConfig


@pytest.fixture
def redis_handler(mocker):
    mocker.patch('redis.StrictRedis.from_url')
    redis_handler = RedisHandler('redis://localhost:6379')
    return redis_handler

def test_send_info_to_redis(redis_handler, mocker):
    mocked_connection = mocker.MagicMock()
    redis_handler.get_connection = mocker.MagicMock(return_value=mocked_connection)
    redis_handler.send_info_to_redis(0, 'test_key', {'message': 'test_message'})
    
    redis_handler.get_connection.assert_called_once_with(0)
    mocked_connection.hmset.assert_called_once_with('test_key', {'message': 'test_message'})

def test_del_info_into_redis(redis_handler, mocker):
    mocked_connection = mocker.MagicMock()
    redis_handler.get_connection = mocker.MagicMock(return_value=mocked_connection)
    redis_handler.del_info_into_redis(0, 'test_key')
    
    redis_handler.get_connection.assert_called_once_with(0)
    mocked_connection.delete.assert_called_once_with('test_key')

def test_get_values_from_redis(redis_handler, mocker):
    mocked_connection = mocker.MagicMock()
    redis_handler.get_connection = mocker.MagicMock(return_value=mocked_connection)
    mocked_connection.hget.side_effect = ['value1', 'value2']
    
    result = redis_handler.get_values_from_redis(0, ['key1', 'key2'], 'field')

    redis_handler.get_connection.assert_called_once_with(0)
    assert result == {'key1': 'value1', 'key2': 'value2'}

def test_get_redis_len(redis_handler, mocker):
    mocked_connection = mocker.MagicMock()
    redis_handler.get_connection = mocker.MagicMock(return_value=mocked_connection)
    mocked_connection.keys.return_value = ['arkadiy_1', 'arkadiy_2']

    result = redis_handler.get_redis_len(0)

    redis_handler.get_connection.assert_called_once_with(0)
    mocked_connection.keys.assert_called_once_with('arkadiy_*')
    assert result == 2

def test_send_error_to_redis(redis_handler, mocker):
    mocked_connection = mocker.MagicMock()
    redis_handler.get_connection = mocker.MagicMock(return_value=mocked_connection)
    mocked_connection.keys.return_value = ['1', '2', '3']
    
    redis_handler.send_error_to_redis(0, 'test_job', '1234567890', 'test_error')
    
    redis_handler.get_connection.assert_called_once_with(0)
    mocked_connection.keys.assert_called_once()
    error_info = {
        "job_name": "test_job",
        "timestamp": "1234567890",
        "error": "test_error",
    }
    mocked_connection.hmset.assert_called_once_with(4, error_info)
    mocked_connection.expire.assert_called_once_with(4, timedelta(days=1))

def test_get_connection(redis_handler, mocker):
    mocked_connection = mocker.MagicMock()
    redis_handler.connections = {1: mocked_connection}

    result = redis_handler.get_connection(1)

    assert result == mocked_connection
import json
import unittest
from unittest.mock import MagicMock, patch, call
from datetime import date
from sqlmodel import Session
from app.models import Incidente, Categoria, Prioridad, Canal, Estado
from app.database import create_incidente_cache, get_engine, obtener_incidente_por_radicado, publish_message, custom_serializer, obtener_incidente_cache, init_db, get_engine_replica, get_session
from uuid import uuid4, UUID
from datetime import datetime
from app import config
import random
import string

class TestIncidenteFunctions(unittest.TestCase):

    def setUp(self):
        self.session_patcher = patch('app.database.Session', autospec=True)
        self.mock_session_class = self.session_patcher.start()
        self.mock_session = MagicMock(spec=Session)
        self.mock_session_class.return_value = self.mock_session

        self.redis_patcher = patch('app.database.Redis', autospec=True)
        self.mock_redis_class = self.redis_patcher.start()
        self.mock_redis = MagicMock()
        self.mock_redis_class.return_value = self.mock_redis

        self.engine_patcher = patch('app.database.engine', autospec=True)
        self.mock_engine = self.engine_patcher.start()

        self.incidente = Incidente(
            id=1,
            cliente_id=123,
            description="Descripción del incidente",
            categoria=Categoria.acceso,
            prioridad=Prioridad.alta,
            canal=Canal.llamada,
            estado=Estado.abierto,
            fecha_creacion=date.today(),
            fecha_cierre=None,
            solucion=None,
            radicado=''.join(random.choices(string.ascii_letters + string.digits, k=8))
        )

    def tearDown(self):
        self.session_patcher.stop()
        self.redis_patcher.stop()
        self.engine_patcher.stop()

    def test_create_incidente_cache_success(self):
        result = create_incidente_cache(
            self.incidente, self.mock_session, self.mock_redis)

        self.mock_session.add.assert_called_once_with(self.incidente)
        self.mock_session.commit.assert_called_once()
        self.mock_session.refresh.assert_called_once_with(self.incidente)
        self.mock_redis.set.assert_called_once_with(
            f"incidente:{self.incidente.id}", self.incidente.model_dump_json())
        self.assertEqual(result, self.incidente)
        self.assertIsInstance(result.radicado, str)

    def test_create_incidente_cache_failure(self):
        self.mock_session.commit.side_effect = Exception(
            "Simulated database error")

        with self.assertRaises(Exception) as context:
            create_incidente_cache(
                self.incidente, self.mock_session, self.mock_redis)

        self.assertIn(
            "Error al crear incidente: Simulated database error", str(context.exception))
        self.mock_session.rollback.assert_called_once()
        self.mock_session.close.assert_called_once()

    @patch('app.database.create_engine')
    def test_get_engine_with_database_url(self, mock_create_engine):
        database_url = "mysql+mysqlconnector://user:password@localhost/dbname"
        engine = get_engine(database_url)
        mock_create_engine.assert_called_once_with(database_url, echo=True)
        self.assertEqual(engine, mock_create_engine.return_value)

    @patch('app.database.create_engine')
    @patch('app.database.config')
    def test_get_engine_with_socket_path(self, mock_config, mock_create_engine):
        mock_config.DB_SOCKET_PATH_PRIMARY = "/cloudsql/project:region:instance"
        mock_config.DB_USER = "user"
        mock_config.DB_PASSWORD = "password"
        mock_config.DB_NAME = "dbname"
        database_url = f"mysql+mysqlconnector://{mock_config.DB_USER}:{mock_config.DB_PASSWORD}@/{mock_config.DB_NAME}"f"?unix_socket={mock_config.DB_SOCKET_PATH_PRIMARY}"

        engine = get_engine()
        mock_create_engine.assert_called_once_with(database_url, echo=True)
        self.assertEqual(engine, mock_create_engine.return_value)

    @patch('app.database.create_engine')
    @patch('app.database.config')
    def test_get_engine_without_socket_path(self, mock_config, mock_create_engine):
        mock_config.DB_SOCKET_PATH_PRIMARY = None
        mock_config.DB_USER = "user"
        mock_config.DB_PASSWORD = "password"
        mock_config.DB_HOST = "localhost"
        mock_config.DB_PORT = "3306"
        mock_config.DB_NAME = "dbname"
        database_url = f"mysql+mysqlconnector://{mock_config.DB_USER}:{mock_config.DB_PASSWORD}@{mock_config.DB_HOST}:{mock_config.DB_PORT}/{mock_config.DB_NAME}"

        engine = get_engine()
        mock_create_engine.assert_called_once_with(database_url, echo=True)
        self.assertEqual(engine, mock_create_engine.return_value)

    def test_obtener_incidente_cache_existente_en_redis(self):
        incidente_json = self.incidente.model_dump_json()
        self.mock_redis.get.return_value = incidente_json

        from app.database import obtener_incidente_cache
        resultado = obtener_incidente_cache(
            self.incidente.id, self.mock_session, self.mock_redis)

        self.mock_session.get.assert_not_called()
        self.assertEqual(resultado, json.loads(incidente_json))
        self.mock_redis.get.assert_called_once_with(
            f"incidente:{self.incidente.id}")

    def test_obtener_incidente_cache_no_existente_en_redis(self):
        self.mock_redis.get.return_value = None

        self.mock_session.get.return_value = self.incidente

        from app.database import obtener_incidente_cache
        resultado = obtener_incidente_cache(
            self.incidente.id, self.mock_session, self.mock_redis)

        self.mock_session.get.assert_called_once_with(
            Incidente, self.incidente.id)

        self.mock_redis.set.assert_called_once_with(
            f"incidente:{self.incidente.id}", self.incidente.model_dump_json())
        self.assertEqual(resultado, self.incidente.model_dump_json())

    def test_create_incidente_cache_without_radicado(self):
        incidente_sin_radicado = Incidente(
            id=1,
            cliente_id=123,
            description="Descripción del incidente",
            categoria=Categoria.acceso,
            prioridad=Prioridad.alta,
            canal=Canal.llamada,
            estado=Estado.abierto,
            fecha_creacion=date.today(),
            fecha_cierre=None,
            solucion=None,
            radicado=None  # Sin radicado
        )

        result = create_incidente_cache(
            incidente_sin_radicado, self.mock_session, self.mock_redis)

        self.mock_session.add.assert_called_once_with(incidente_sin_radicado)
        self.mock_session.commit.assert_called_once()
        self.mock_session.refresh.assert_called_once_with(incidente_sin_radicado)
        self.mock_redis.set.assert_called_once_with(
            f"incidente:{incidente_sin_radicado.id}", incidente_sin_radicado.model_dump_json())
        
        # Asegurarse de que el radicado fue generado
        self.assertIsInstance(result.radicado, str)
        
    def test_obtener_incidente_por_radicado_no_existente(self):
        radicado_inexistente = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

        # Simular que no está en Redis ni en la base de datos
        self.mock_redis.get.return_value = None
        self.mock_session.query().filter_by().first.return_value = None

        resultado = obtener_incidente_por_radicado(
            radicado_inexistente, self.mock_session, self.mock_redis)

        # Verificar que se devolvió None
        self.assertIsNone(resultado)

        self.mock_redis.get.assert_called_once_with(f"incidente:radicado:{radicado_inexistente}")
        
    def test_obtener_incidente_por_radicado_existente_en_redis(self):
        radicado_existente = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        incidente_json = self.incidente.model_dump_json()

        # Simular que el incidente está en Redis
        self.mock_redis.get.return_value = incidente_json

        resultado = obtener_incidente_por_radicado(
            radicado_existente, self.mock_session, self.mock_redis)

        # Verificar que el incidente fue cargado desde Redis
        self.mock_redis.get.assert_called_once_with(f"incidente:radicado:{radicado_existente}")
        self.assertEqual(resultado.id, self.incidente.id)
        self.assertEqual(resultado.radicado, self.incidente.radicado.__str__())
    
    def test_publish_message_in_testing(self):
        with patch('app.database.config.is_testing', return_value=True), \
             patch('app.database.service_account.Credentials.from_service_account_file') as mock_credentials, \
             patch('app.database.pubsub_v1.PublisherClient') as mock_publisher:
            
            data = {"message": "Test Message"}
            publish_message(data, config.TOPIC_ID)
            
            # Check that no publishing actions were taken
            mock_credentials.assert_not_called()
            mock_publisher.assert_not_called()

    def test_custom_serializer_with_supported_types(self):
        date_obj = datetime(2023, 10, 26)
        uuid_obj = uuid4()

        self.assertEqual(custom_serializer(date_obj), date_obj.isoformat())
        self.assertEqual(custom_serializer(uuid_obj), str(uuid_obj))

    def test_custom_serializer_with_unsupported_type(self):
        with self.assertRaises(TypeError):
            custom_serializer({"unsupported": "type"})

    @patch('app.database.SQLModel.metadata.create_all')
    def test_init_db(self, mock_create_all):
        engine = MagicMock()
        engine_replica = MagicMock()
        
        init_db(engine, engine_replica)
        
        mock_create_all.assert_has_calls([call(engine), call(engine_replica)], any_order=True)

    def test_obtener_incidente_cache_database_failure(self):
        self.mock_redis.get.return_value = None
        self.mock_session.get.side_effect = Exception("Database failure")

        with self.assertRaises(Exception):
            obtener_incidente_cache(self.incidente.id, self.mock_session, self.mock_redis)
        self.mock_redis.get.assert_called_once_with(f"incidente:{self.incidente.id}")

    def test_obtener_incidente_por_radicado_miss_in_redis_and_database(self):
        self.mock_redis.get.return_value = None
        self.mock_session.query().filter_by().first.return_value = None

        result = obtener_incidente_por_radicado(self.incidente.radicado, self.mock_session, self.mock_redis)
        self.assertIsNone(result)
        self.mock_redis.get.assert_called_once_with(f"incidente:radicado:{self.incidente.radicado}")

    def test_custom_serializer_with_datetime_and_uuid(self):
        now = datetime.now()
        id = uuid4()
        self.assertEqual(custom_serializer(now), now.isoformat())
        self.assertEqual(custom_serializer(id), str(id))

    def test_custom_serializer_with_invalid_type(self):
        with self.assertRaises(TypeError):
            custom_serializer({"unsupported": "data"})

    def test_publish_message_in_testing(self):
        # Mock the config to simulate testing environment
        with patch("app.database.config.is_testing", return_value=True), \
             patch("app.database.service_account.Credentials.from_service_account_file") as mock_credentials, \
             patch("app.database.pubsub_v1.PublisherClient") as mock_publisher:
            
            data = {"message": "Test message"}
            
            # Call the function
            publish_message(data, config.TOPIC_ID)
            
            # Ensure no credentials or publisher are created in testing mode
            mock_credentials.assert_not_called()
            mock_publisher.assert_not_called()
    
    @patch('app.database.create_engine')
    @patch('app.database.config')
    def test_get_engine_replica_with_socket_path(self, mock_config, mock_create_engine):
        mock_config.DB_SOCKET_PATH_REPLICA = "/cloudsql/project:region:instance"
        mock_config.DB_USER_REPLICA = "replica_user"
        mock_config.DB_PASSWORD_REPLICA = "replica_password"
        mock_config.DB_NAME_REPLICA = "replica_db"
        
        database_url = f"mysql+mysqlconnector://{mock_config.DB_USER_REPLICA}:{mock_config.DB_PASSWORD_REPLICA}@/{mock_config.DB_NAME_REPLICA}?unix_socket={mock_config.DB_SOCKET_PATH_REPLICA}"
        engine = get_engine_replica()
        
        mock_create_engine.assert_called_once_with(database_url, echo=True)
        self.assertEqual(engine, mock_create_engine.return_value)

    def test_create_incidente_cache_with_existing_radicado(self):
        self.incidente.radicado = ''.join(random.choices(string.ascii_letters + string.digits, k=8))  # Assign an existing alphanumeric radicado
        result = create_incidente_cache(
            self.incidente, self.mock_session, self.mock_redis
        )
        self.mock_session.commit.assert_called_once()
        self.assertEqual(result.radicado, self.incidente.radicado)

    def test_create_incidente_cache_redis_failure(self):
        # Simulate Redis failure by making set raise an exception
        self.mock_redis.set.side_effect = Exception("Redis failure")
        with self.assertRaises(Exception) as context:
            create_incidente_cache(self.incidente, self.mock_session, self.mock_redis)
        self.assertIn("Redis failure", str(context.exception))
        self.mock_session.rollback.assert_called_once()

    # Additional Tests for `obtener_incidente_cache`
    def test_obtener_incidente_cache_not_in_redis_or_db(self):
        self.mock_redis.get.return_value = None  # Not in Redis
        self.mock_session.get.return_value = None  # Not in DB

        result = obtener_incidente_cache(
            self.incidente.id, self.mock_session, self.mock_redis
        )
        self.assertIsNone(result)

    # Additional Tests for `custom_serializer`
    def test_custom_serializer_with_nested_types(self):
        nested_data = {
            "date": datetime(2023, 10, 26),
            "uuid": uuid4(),
            "list": [1, 2, 3],
        }
        serialized_data = json.dumps(nested_data, default=custom_serializer)
        self.assertIn(nested_data["date"].isoformat(), serialized_data)
        self.assertIn(str(nested_data["uuid"]), serialized_data)

    # Additional Tests for `get_engine` and `get_engine_replica`
    @patch('app.database.create_engine')
    def test_get_engine_invalid_url(self, mock_create_engine):
        mock_create_engine.side_effect = Exception("Invalid URL")
        with self.assertRaises(Exception):
            get_engine("invalid_database_url")


    @patch('app.database.create_engine')
    def test_get_engine_replica_invalid_url(self, mock_create_engine):
        mock_create_engine.side_effect = Exception("Invalid URL")
        with self.assertRaises(Exception):
            get_engine_replica("invalid_database_url")

    @patch('app.database.SQLModel.metadata.create_all')
    def test_init_db_primary_and_replica(self, mock_create_all):
        engine = MagicMock()
        engine_replica = MagicMock()
        init_db(engine, engine_replica)
        mock_create_all.assert_has_calls([call(engine), call(engine_replica)], any_order=True)

    @patch('app.database.config.is_testing', return_value=False)
    @patch('app.database.pubsub_v1.PublisherClient')
    @patch('app.database.config')
    def test_publish_message_non_testing(self, mock_config, mock_publisher_client, mock_is_testing):
        mock_config.PROJECT_ID = "test_project"
        mock_config.TOPIC_ID = "test_topic"

        mock_publisher_instance = mock_publisher_client.return_value
        mock_future = MagicMock()
        mock_future.result.return_value = "mock_message_id"
        mock_publisher_instance.publish.return_value = mock_future

        data = {"message": "Test message"}
        
        publish_message(data, config.TOPIC_ID)

        topic_path = mock_publisher_instance.topic_path("test_project", "test_topic")
        message_data = json.dumps(data, default=custom_serializer).encode("utf-8")
        
        mock_publisher_instance.publish.assert_called_once_with(topic_path, message_data)
        self.assertEqual(mock_future.result.call_count, 1)



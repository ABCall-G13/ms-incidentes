import json
import unittest
from unittest.mock import MagicMock, patch, call
from datetime import date
from sqlmodel import Session
from app.models import Incidente, Categoria, Prioridad, Canal, Estado
from app.database import create_incidente_cache, get_engine, get_session, get_redis_client, obtener_incidente_por_radicado, publish_message, custom_serializer, obtener_incidente_cache, init_db
from uuid import uuid4, UUID
from datetime import datetime
from app import config

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
            radicado=uuid4()
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
        self.assertIsInstance(result.radicado, UUID)

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
        # Crear un incidente sin radicado
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
        self.assertIsInstance(result.radicado, UUID)
        
    def test_obtener_incidente_por_radicado_no_existente(self):
        radicado_inexistente = uuid4()

        # Simular que no está en Redis ni en la base de datos
        self.mock_redis.get.return_value = None
        self.mock_session.query().filter_by().first.return_value = None

        resultado = obtener_incidente_por_radicado(
            radicado_inexistente, self.mock_session, self.mock_redis)

        # Verificar que se devolvió None
        self.assertIsNone(resultado)

        self.mock_redis.get.assert_called_once_with(f"incidente:radicado:{radicado_inexistente}")

        
        
    def test_obtener_incidente_por_radicado_existente_en_redis(self):
        radicado_existente = uuid4()
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
            publish_message(data)
            
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
        
        # Ensure that `create_all` was called for both the main and replica engines
        mock_create_all.assert_has_calls([call(engine), call(engine_replica)], any_order=True)

    # @patch('app.database.config')
    # def test_get_engine_without_url(self, mock_config):
    #     # Set up config values for primary database
    #     mock_config.DB_SOCKET_PATH_PRIMARY = "/cloudsql/socket_path"
    #     mock_config.DB_USER = "user"
    #     mock_config.DB_PASSWORD = "password"
    #     mock_config.DB_NAME = "dbname"

    #     # Call get_engine without database_url
    #     engine = get_engine()
    #     self.assertIn("user:password@/", engine.url)

    # def test_get_session_yields_session(self):
    #     # Mock the engine and get_session to yield sessions
    #     with patch('app.database.engine') as mock_engine:
    #         with patch('app.database.Session', return_value=self.mock_session):
    #             generator = get_session()
    #             session = next(generator)
    #             self.assertIsInstance(session, Session)

    # def test_get_redis_client(self):
    #     # Verify Redis client is created with correct configuration
    #     client = get_redis_client()
    #     self.assertEqual(client, self.mock_redis)
    #     self.mock_redis.__init__.assert_called_once_with(host=config.REDIS_HOST, port=config.REDIS_PORT)

    def test_obtener_incidente_cache_database_failure(self):
        # Simulate Redis cache miss and database retrieval failure
        self.mock_redis.get.return_value = None
        self.mock_session.get.side_effect = Exception("Database failure")

        # Execute test
        with self.assertRaises(Exception):
            obtener_incidente_cache(self.incidente.id, self.mock_session, self.mock_redis)
        self.mock_redis.get.assert_called_once_with(f"incidente:{self.incidente.id}")

    def test_obtener_incidente_por_radicado_miss_in_redis_and_database(self):
        # Configure Redis and database to return None (cache miss and DB miss)
        self.mock_redis.get.return_value = None
        self.mock_session.query().filter_by().first.return_value = None

        # Call function and verify it returns None
        result = obtener_incidente_por_radicado(self.incidente.radicado, self.mock_session, self.mock_redis)
        self.assertIsNone(result)
        self.mock_redis.get.assert_called_once_with(f"incidente:radicado:{self.incidente.radicado}")

    def test_custom_serializer_with_datetime_and_uuid(self):
        # Test that custom serializer works correctly
        now = datetime.now()
        id = uuid4()
        self.assertEqual(custom_serializer(now), now.isoformat())
        self.assertEqual(custom_serializer(id), str(id))

    def test_custom_serializer_with_invalid_type(self):
        # Test that an unsupported type raises a TypeError
        with self.assertRaises(TypeError):
            custom_serializer({"unsupported": "data"})
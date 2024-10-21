import json
import unittest
from unittest.mock import MagicMock, patch
from datetime import date
from sqlmodel import Session
from app.models import Incidente, Categoria, Prioridad, Canal, Estado
from app.database import create_incidente_cache, get_engine, get_redis_client


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
            solucion=None
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
        database_url = f"mysql+mysqlconnector://{mock_config.DB_USER}:{mock_config.DB_PASSWORD}@/{
            mock_config.DB_NAME}?unix_socket={mock_config.DB_SOCKET_PATH_PRIMARY}"

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
        database_url = f"mysql+mysqlconnector://{mock_config.DB_USER}:{mock_config.DB_PASSWORD}@{
            mock_config.DB_HOST}:{mock_config.DB_PORT}/{mock_config.DB_NAME}"

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

    def test_obtener_incidente_cache_no_existente_en_redis_ni_db(self):
        self.mock_redis.get.return_value = None
        self.mock_session.get.return_value = None

        from app.database import obtener_incidente_cache
        resultado = obtener_incidente_cache(
            self.incidente.id, self.mock_session, self.mock_redis)

        self.mock_session.get.assert_called_once_with(
            Incidente, self.incidente.id)

        self.mock_redis.set.assert_not_called()
        self.assertIsNone(resultado)

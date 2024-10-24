import json
import unittest
from unittest.mock import MagicMock, patch
from datetime import date
from sqlmodel import Session
from app.models import Incidente, Categoria, Prioridad, Canal, Estado
from app.database import create_incidente_cache, get_engine, get_redis_client, obtener_incidente_por_radicado
from uuid import uuid4, UUID


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




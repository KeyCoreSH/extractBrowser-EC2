"""Offline compatibility checks for security dependency updates (no AWS/OpenAI calls)."""
import importlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

class DependencySmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.previous = os.getcwd()
        os.chdir(cls.temp.name)
        Path('data').mkdir()
        cls.env = patch.dict(os.environ, {
            'APP_ENV': 'development', 'SECRET_KEY': 'test-only-not-a-secret',
            'DEFAULT_ADMIN_EMAIL': 'test@example.invalid',
            'DEFAULT_ADMIN_PASSWORD': 'local-test-password',
            'API_ACCESS_TOKEN': 'local-test-token',
            'AWS_EC2_METADATA_DISABLED': 'true',
        })
        cls.env.start()
        with patch('dotenv.load_dotenv'), patch('utils.s3_manager.S3Manager') as s3, patch('services.ai_service.AIService') as ai:
            s3.return_value.test_connection.return_value = True
            s3.return_value.list_files.return_value = []
            ai.return_value.openai_available = False
            cls.module = importlib.import_module('app')
        cls.app = cls.module.app
        cls.app.config['TESTING'] = True

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            cls.module.db.session.remove()
            cls.module.db.engine.dispose()
        cls.env.stop()
        os.chdir(cls.previous)
        cls.temp.cleanup()

    def setUp(self):
        self.client = self.app.test_client()

    def test_health_and_cors_preflight(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['status'], 'healthy')
        response = self.client.options('/upload', headers={'Origin': 'https://example.invalid', 'Access-Control-Request-Method': 'POST'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(response.headers['Access-Control-Allow-Origin'], ('*', 'https://example.invalid'))

    def test_json_login_session_and_invalid_credentials(self):
        self.assertEqual(self.client.post('/login', json={'email':'test@example.invalid','password':'wrong'}).status_code,401)
        response = self.client.post('/login', json={'email':'test@example.invalid','password':'local-test-password'})
        self.assertEqual(response.status_code,200)
        self.assertTrue(response.json['success'])
        self.assertEqual(self.client.get('/').status_code,200)

    def test_form_login(self):
        response = self.client.post('/login', data={'email':'test@example.invalid','password':'local-test-password'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(self.client.get('/').status_code,200)

    def test_upload_auth_and_empty_payloads(self):
        self.assertEqual(self.client.post('/upload', json={'file_content':''}).status_code,401)
        headers={'X-API-Key':'local-test-token'}
        self.assertEqual(self.client.post('/upload', json={'file_content':''}, headers=headers).status_code,400)
        self.assertEqual(self.client.post('/upload', data={'file':(io.BytesIO(b''),'empty.pdf')}, headers=headers).status_code,400)

if __name__ == '__main__':
    unittest.main()

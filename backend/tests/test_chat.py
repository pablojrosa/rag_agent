import os
import unittest
from unittest.mock import patch

os.environ['LANGFUSE_ENABLED'] = 'false'
os.environ['DATABASE_URL'] = 'sqlite://'
from main import app, db
from src.app.models import ChatMessage


class ChatTests(unittest.TestCase):
    def setUp(self):
        self.context = app.app_context()
        self.context.push()
        db.create_all()
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    @patch('main.answer_question', return_value='Answer')
    def test_chat_persists_without_langfuse(self, answer):
        response = self.client.post('/chat', json={'message': 'Question', 'session_id': 'session'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['response'], 'Answer')
        self.assertEqual(ChatMessage.query.count(), 2)

    @patch('main.answer_question', side_effect=RuntimeError('provider failure'))
    def test_provider_error_does_not_save_partial_conversation(self, answer):
        response = self.client.post('/chat', json={'message': 'Question', 'session_id': 'session'})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(ChatMessage.query.count(), 0)
        self.assertNotIn('provider failure', response.json['error'])

    def test_invalid_input_is_rejected(self):
        self.assertEqual(self.client.post('/chat', json=[]).status_code, 400)
        self.assertEqual(self.client.get('/conversation-metrics?days=0').status_code, 400)

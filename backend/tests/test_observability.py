import unittest
from unittest.mock import MagicMock, patch

from src.app.observability import observation


class TelemetryTests(unittest.TestCase):
    @patch('src.app.observability.get_client', side_effect=RuntimeError('unavailable'))
    def test_export_failure_does_not_stop_work(self, client):
        with observation('test') as span:
            span.update(output='answer')
            self.assertIsNone(span.trace_id)

    @patch('src.app.observability.get_client')
    def test_application_error_propagates_once(self, get_client):
        manager = MagicMock()
        get_client.return_value.start_as_current_observation.return_value = manager
        with self.assertRaisesRegex(ValueError, 'application error'):
            with observation('test'):
                raise ValueError('application error')
        manager.__enter__.return_value.update.assert_called_with(level='ERROR', status_message='ValueError')
        manager.__exit__.assert_called_once()

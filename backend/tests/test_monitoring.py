import json
import unittest
from unittest.mock import MagicMock, patch

from src.app.monitoring import monitoring_payload, scores_map, scores_for, MonitoringUnavailable


CATALOG = [{'key': 'config-1', 'name': 'groundedness_v1', 'label': 'Groundedness', 'type': 'NUMERIC'}]


class MonitoringTests(unittest.TestCase):
    def test_zero_score_and_reason_are_preserved(self):
        mapped = scores_map([{'name': 'groundedness_v1', 'data_type': 'NUMERIC',
                              'value': 0, 'comment': 'Unsupported', 'timestamp': '2026-01-01'}], list(CATALOG))
        self.assertEqual(mapped['config-1']['value'], 0)
        self.assertEqual(mapped['config-1']['comment'], 'Unsupported')

    def test_empty_scores_are_not_zero(self):
        self.assertEqual(scores_map([], list(CATALOG)), {})

    def test_score_pagination(self):
        client = MagicMock()
        client.api.scores_v3.get_many_v3.side_effect = [
            {'data': [{'id': 'first'}], 'meta': {'cursor': 'next'}},
            {'data': [{'id': 'second'}], 'meta': {'cursor': None}}]
        self.assertEqual(len(scores_for(client, observation_id='observation')), 2)
        self.assertEqual(client.api.scores_v3.get_many_v3.call_args.kwargs['cursor'], 'next')

    @patch('src.app.monitoring.get_client', return_value=None)
    def test_missing_configuration_is_explicit(self, client):
        self.assertFalse(monitoring_payload('online')['configured'])

    @patch('src.app.monitoring.get_client', side_effect=RuntimeError('secret detail'))
    def test_service_failure_is_not_an_empty_dashboard(self, client):
        with self.assertRaises(MonitoringUnavailable):
            monitoring_payload('online')

    @patch('src.app.monitoring.definitions', return_value=CATALOG)
    @patch('src.app.monitoring.get_client')
    def test_filters_pagination_and_string_io(self, get_client, definitions):
        client = get_client.return_value
        client.api.metrics.metrics.return_value = {'data': []}
        client.api.observations.get_many.return_value = {
            'data': [{'id': 'obs', 'trace_id': 'trace', 'input': '{"question":"Question"}',
                      'output': '"Answer"', 'start_time': '2026-09-08T10:00:00Z',
                      'end_time': '2026-09-08T10:00:02Z', 'level': 'DEFAULT'}],
            'meta': {'cursor': 'page-two'}}
        client.api.scores_v3.get_many_v3.return_value = {'data': [], 'meta': {}}
        response = monitoring_payload('online', cursor='page-one')
        query = client.api.observations.get_many.call_args.kwargs
        filters = json.loads(query['filter'])
        self.assertEqual({item['column'] for item in filters}, {'name', 'environment', 'startTime', 'metadata'})
        self.assertNotIn('parse_io_as_json', query)
        self.assertEqual(query['cursor'], 'page-one')
        self.assertEqual(response['next_cursor'], 'page-two')
        row = response['rows'][0]
        self.assertEqual(row['question'], 'Question')
        self.assertEqual(row['answer'], 'Answer')
        self.assertEqual(row['latency_seconds'], 2)
        self.assertEqual(row['status'], 'unscored')

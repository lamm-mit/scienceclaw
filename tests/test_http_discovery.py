import unittest
from unittest.mock import patch, MagicMock
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from coordination.agent_discovery import AgentDiscoveryService


class TestHttpDiscovery(unittest.TestCase):
    def setUp(self):
        self.svc = AgentDiscoveryService()

    @patch('coordination.agent_discovery.requests')
    def test_http_discover_returns_sessions_and_needs(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {
            'sessions': [{'id': 'abc', 'topic': 'CRISPR', 'joinCode': 'XY12AB34'}],
            'needs': [{'id': 'n1', 'query': 'blast search', 'preferredSkills': ['blast']}],
            'matchedOn': ['blast'],
        }
        mock_requests.get.return_value = mock_resp

        result = self.svc.http_discover(skills=['blast'], base_url='http://localhost:3000')
        self.assertIn('sessions', result)
        self.assertIn('needs', result)
        self.assertEqual(len(result['sessions']), 1)
        self.assertEqual(result['sessions'][0]['id'], 'abc')

    @patch('coordination.agent_discovery.requests')
    def test_http_discover_handles_error(self, mock_requests):
        mock_requests.get.side_effect = Exception('connection refused')
        result = self.svc.http_discover(skills=['pubmed'], base_url='http://dead')
        self.assertEqual(result, {'sessions': [], 'needs': [], 'matchedOn': []})


    @patch('coordination.agent_discovery.requests')
    def test_http_discover_handles_non_ok_response(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_requests.get.return_value = mock_resp
        result = self.svc.http_discover(skills=['blast'], base_url='http://localhost:3000')
        self.assertEqual(result, {'sessions': [], 'needs': [], 'matchedOn': []})


if __name__ == '__main__':
    unittest.main()

import tempfile
import unittest
import requests
from unittest.mock import Mock, patch
from crosslinked.searxng import SearXNG


def response(payload):
    value = Mock(status_code=200)
    value.json.return_value = payload
    return value


class ReliabilityTests(unittest.TestCase):
    def run_search(self, provider, payloads):
        with patch('crosslinked.searxng.requests.Session') as session:
            get = session.return_value.__enter__.return_value.get
            get.side_effect = [response(p) for p in payloads]
            provider.search()
            return get

    def test_selected_engines_and_empty_failure_reason(self):
        provider = SearXNG('Example', 'http://localhost:8080', engines=['bing', 'mojeek'])
        get = self.run_search(provider, [{'results': [], 'unresponsive_engines': [['bing', 'timeout']]}])
        self.assertEqual(get.call_args.kwargs['params']['engines'], 'bing,mojeek')
        self.assertNotIn('categories', get.call_args.kwargs['params'])
        self.assertEqual(provider.stop_reason, 'empty_page_with_engine_failures')
        self.assertEqual(provider.status, 'partial')

    def test_resume_complete_pages_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            first = SearXNG('Example', 'http://localhost:8080', cache_dir=directory)
            self.run_search(first, [{'results': []}])
            second = SearXNG('Example', 'http://localhost:8080', cache_dir=directory, resume=True)
            get = self.run_search(second, [])
            get.assert_not_called()
            self.assertEqual(second.stop_reason, 'empty_page')

    def test_partial_cache_retried_and_evidence_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            provider = SearXNG('Example', 'http://localhost:8080', cache_dir=directory, resume=True)
            provider.save_page(1, {'results': [{'url': 'https://linkedin.com/in/jane-example',
                                              'title': 'Jane Example - Lecturer at Example'}],
                                   'unresponsive_engines': [['bing', 'timeout']]})
            get = self.run_search(provider, [{'results': []}])
            self.assertEqual(get.call_count, 1)
            self.assertEqual(len(provider.results), 1)
            third = SearXNG('Example', 'http://localhost:8080', cache_dir=directory, resume=True)
            get = self.run_search(third, [])
            get.assert_not_called()
            self.assertEqual(len(third.results), 1)

    def test_cache_identity_includes_engines_and_target(self):
        first = SearXNG('Example', 'http://localhost:8080', engines=['bing'], cache_dir='cache')
        second = SearXNG('Example', 'http://localhost:8080', engines=['google'], cache_dir='cache')
        third = SearXNG('Other', 'http://localhost:8080', engines=['bing'], cache_dir='cache')
        self.assertNotEqual(first.cache_path(1), second.cache_path(1))
        self.assertNotEqual(first.cache_path(1), third.cache_path(1))

    def test_corrupt_cache_falls_back_to_request(self):
        with tempfile.TemporaryDirectory() as directory:
            provider = SearXNG('Example', 'http://localhost:8080', cache_dir=directory, resume=True)
            provider.cache_path(1).write_text('not json')
            get = self.run_search(provider, [{'results': []}])
            self.assertEqual(get.call_count, 1)

    def test_expired_budget_has_explicit_reason(self):
        provider = SearXNG('Example', 'http://localhost:8080', timeout=1)
        with patch('crosslinked.searxng.monotonic', side_effect=[0, 2]):
            self.run_search(provider, [])
        self.assertEqual(provider.stop_reason, 'time_budget')

    def test_request_timeout_respects_remaining_budget(self):
        provider = SearXNG('Example', 'http://localhost:8080', timeout=60, request_timeout=30)
        with patch('crosslinked.searxng.monotonic', side_effect=[0, 40, 40, 40]):
            get = self.run_search(provider, [{'results': []}])
        self.assertEqual(get.call_args.kwargs['timeout'], 20)

    def test_engine_validation(self):
        provider = SearXNG('Example', 'http://localhost:8080', engines=['bing'])
        with patch('crosslinked.searxng.requests.get', return_value=response({'engines': [{'name': 'bing', 'enabled': False}]})):
            provider.validate_engines()
            provider.engines = ['typo']
            with self.assertRaisesRegex(ValueError, 'Unknown'):
                provider.validate_engines()

    def test_transient_retry_and_budget(self):
        provider = SearXNG('Example', 'http://localhost:8080', retries=2)
        session = Mock()
        session.get.side_effect = [requests.Timeout('temporary'), response({'results': []})]
        with patch('crosslinked.searxng.sleep') as wait:
            provider.request_page(session, {}, 30)
            wait.assert_called_once_with(2)
        session.get.side_effect = requests.Timeout('temporary')
        with patch('crosslinked.searxng.sleep') as wait:
            with self.assertRaises(requests.Timeout):
                provider.request_page(session, {}, 1)
            wait.assert_not_called()

    def test_denied_and_rate_limited_not_retried(self):
        provider = SearXNG('Example', 'http://localhost:8080', retries=2)
        for status in (403, 429):
            session = Mock()
            session.get.return_value = Mock(status_code=status)
            self.assertEqual(provider.request_page(session, {}, 30).status_code, status)
            self.assertEqual(session.get.call_count, 1)

    def test_retry_after_not_shortened(self):
        provider = SearXNG('Example', 'http://localhost:8080', retries=2)
        r = requests.Response()
        r.status_code = 503
        r.headers['Retry-After'] = '120'
        session = Mock()
        session.get.return_value = r
        with patch('crosslinked.searxng.sleep') as wait:
            with self.assertRaises(requests.HTTPError):
                provider.request_page(session, {}, 30)
            wait.assert_not_called()

    def test_resume_continues_after_cached_page(self):
        with tempfile.TemporaryDirectory() as directory:
            provider = SearXNG('Example', 'http://localhost:8080', jitter=0, cache_dir=directory, resume=True)
            provider.save_page(1, {'results': [{'url': 'https://linkedin.com/in/jane-example', 'title': 'Jane Example - Lecturer'}]})
            get = self.run_search(provider, [{'results': [{'url': 'https://linkedin.com/in/john-example', 'title': 'John Example - Student'}]}, {'results': []}])
            self.assertEqual([c.kwargs['params']['pageno'] for c in get.call_args_list], [2, 3])
            self.assertEqual(len(provider.results), 2)


if __name__ == '__main__':
    unittest.main()

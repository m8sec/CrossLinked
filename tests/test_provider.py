"""Provider interface contract: run(), validation failures, and the legacy HTML provider."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests

from crosslinked import build_provider
from crosslinked.models import Candidate
from crosslinked.provider import Provider
from crosslinked.search import CrossLinked
from crosslinked.searxng import SearXNG


class Stub(Provider):
    name = 'stub'

    def __init__(self, *args, fail_validation=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fail_validation = fail_validation

    def validate(self):
        if self.fail_validation:
            raise ValueError('bad config')

    def search(self):
        self.add_result(Candidate(name='jane doe', url='https://www.linkedin.com/in/jane'))
        self.add_result(Candidate(name='jane doe', url='https://www.linkedin.com/in/jane'))
        self.add_result(Candidate(name='linkedin.com', url='https://www.linkedin.com/in/x'))
        self.state.finish('complete', 'page_limit')
        return self.results


class ProviderContractTests(unittest.TestCase):
    def test_run_records_state_and_fills_provenance(self):
        provider = Stub('Example')
        seen = []
        provider.sinks.append(seen.append)
        results = provider.run()
        self.assertEqual(len(results), 1)
        self.assertEqual(seen, results)
        self.assertEqual(results[0].provider, 'stub')
        self.assertTrue(results[0].observed_at)
        self.assertEqual(provider.state.records, 1)
        self.assertEqual(provider.state.status, 'complete')
        self.assertTrue(provider.state.started_at and provider.state.finished_at)

    def test_validation_failure_is_failed_state(self):
        provider = Stub('Example', fail_validation=True)
        self.assertEqual(provider.run(), [])
        self.assertEqual(provider.status, 'failed')
        self.assertEqual(provider.stop_reason, 'validation_failed')
        self.assertIn('bad config', provider.warnings[0])

    def test_searxng_validation_through_run(self):
        provider = SearXNG('Example', 'http://localhost:8080', engines=['typo'])
        with patch('crosslinked.searxng.requests.get', side_effect=requests.ConnectionError('down')):
            self.assertEqual(provider.run(), [])
        self.assertEqual(provider.state.status, 'failed')
        self.assertEqual(provider.state.stop_reason, 'validation_failed')

    def test_build_provider(self):
        args = SimpleNamespace(company_name='Example', searxng_url='http://localhost:8080', timeout=5, jitter=0,
                               max_pages=1, proxy=[], searxng_engines=None, cache_dir=None, resume=False,
                               request_timeout=5, retries=0)
        self.assertIsInstance(build_provider('searxng', args), SearXNG)
        google = build_provider('google', args)
        self.assertIsInstance(google, CrossLinked)
        self.assertEqual(google.name, 'google')
        with self.assertRaises(ValueError):
            build_provider('unknown', args)


class LegacyProviderTests(unittest.TestCase):
    def html(self, *links):
        body = ''.join('<a href="{}">{}</a>'.format(href, text) for href, text in links)
        return Mock(status_code=200, content=('<html><body>' + body + '</body></html>').encode())

    def test_blocked_engine_is_failed(self):
        provider = CrossLinked('google', 'Example', timeout=5, jitter=0)
        with patch('crosslinked.search.web_request', return_value=Mock(status_code=429)):
            self.assertEqual(provider.run(), [])
        self.assertEqual(provider.status, 'failed')
        self.assertEqual(provider.stop_reason, 'http_429')
        self.assertEqual(provider.state.pages, 1)

    def test_connection_error_is_request_failure(self):
        provider = CrossLinked('bing', 'Example', timeout=5, jitter=0)
        with patch('crosslinked.search.web_request', return_value=False):
            provider.run()
        self.assertEqual(provider.stop_reason, 'request_failure')

    def test_time_budget_is_limited_and_parses_profiles(self):
        provider = CrossLinked('bing', 'Example', timeout=0.3, jitter=0.05)
        page = self.html(('https://www.linkedin.com/in/jane-doe', 'Jane Doe - Engineer at Example | LinkedIn'),
                         ('https://www.linkedin.com/in/jane-doe', 'Jane Doe - Engineer at Example | LinkedIn'),
                         ('https://www.linkedin.com/company/example', 'Example'),
                         ('https://example.org', 'Unrelated'))
        with patch('crosslinked.search.web_request', return_value=page):
            results = provider.run()
        self.assertEqual(provider.status, 'limited')
        self.assertEqual(provider.stop_reason, 'time_budget')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, 'jane doe')
        self.assertEqual(results[0].title, 'Engineer at Example')
        self.assertEqual(results[0].provider, 'bing')
        self.assertGreater(provider.state.pages, 1)


if __name__ == '__main__':
    unittest.main()

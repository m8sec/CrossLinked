import csv
import io
import unittest
from unittest.mock import Mock, patch
import requests
from crosslinked import cli
from crosslinked.searxng import SearXNG, search_endpoint


def result(title='Jane Doe - Engineer | LinkedIn'):
    return {'url': 'https://www.linkedin.com/in/jane-doe', 'title': title}


def response(payload=None, status=200):
    value = Mock(status_code=status)
    value.json.return_value = payload
    if status >= 400:
        value.raise_for_status.side_effect = requests.HTTPError(str(status))
    return value


class ProviderTests(unittest.TestCase):
    def provider(self, **kwargs):
        return SearXNG('Example & Co', 'http://localhost:8080', jitter=0, **kwargs)

    def run_pages(self, provider, pages):
        with patch('crosslinked.searxng.requests.Session') as session:
            get = session.return_value.__enter__.return_value.get
            get.side_effect = pages
            return provider.search(), get.call_args_list

    def test_endpoint(self):
        for value in ('http://localhost:8080', 'http://localhost:8080/search/'):
            self.assertEqual(search_endpoint(value), 'http://localhost:8080/search')
        self.assertEqual(search_endpoint('https://example.org/prefix'), 'https://example.org/prefix/search')
        for value in ('file:///tmp', 'https://user:pass@example.org', 'https://example.org?q=x'):
            with self.assertRaises(ValueError):
                search_endpoint(value)

    def test_pagination_independent_of_extracted_count(self):
        provider = self.provider()
        records, calls = self.run_pages(provider, [
            response({'results': [{'url': 'https://example.org', 'title': 'Unrelated'}]}),
            response({'results': [result()]}), response({'results': []})])
        self.assertEqual(len(records), 1)
        self.assertEqual([c.kwargs['params']['pageno'] for c in calls], [1, 2, 3])
        self.assertEqual(calls[0].kwargs['params']['q'], 'site:linkedin.com/in "Example & Co"')
        self.assertNotIn('verify', calls[0].kwargs)
        self.assertEqual(provider.status, 'complete')

    def test_dedup_and_repeated_page(self):
        provider = self.provider()
        duplicate = result()
        duplicate['url'] = 'https://au.linkedin.com/in/jane-doe/?trk=search'
        payload = {'results': [result(), duplicate]}
        records, calls = self.run_pages(provider, [response(payload), response(payload)])
        self.assertEqual(len(records), 1)
        self.assertEqual(len(calls), 2)
        self.assertEqual(provider.status, 'limited')

    def test_reject_nonprofiles(self):
        provider = self.provider()
        for url in ('https://notlinkedin.com/in/jane', 'https://linkedin.com.evil.org/in/jane',
                    'https://linkedin.com/company/example', 'https://linkedin.com/in/',
                    'https://linkedin.com/in/jane/details', 'javascript:alert(1)'):
            self.assertIsNone(provider.parse_result({'url': url, 'title': 'Jane Doe'}))
        for item in (None, {}, {'url': [], 'title': 2}):
            self.assertIsNone(provider.parse_result(item))

    def test_hyphenated_name(self):
        record = self.provider().parse_result(result('Anne-Marie Dupont – Senior Engineer | LinkedIn'))
        self.assertEqual(record['name'], 'anne-marie dupont')
        self.assertEqual(record['title'], 'Senior Engineer')

    def test_failures_not_empty_success(self):
        invalid = response()
        invalid.json.side_effect = ValueError('Not JSON')
        for page in (response(status=403), response(status=429), invalid,
                     response({'unexpected': []}), requests.Timeout('timeout')):
            provider = self.provider()
            records, _ = self.run_pages(provider, [page])
            self.assertEqual(records, [])
            self.assertEqual(provider.status, 'failed')

    def test_partial_results_survive_failure(self):
        provider = self.provider()
        records, _ = self.run_pages(provider, [response({'results': [result()]}), response(status=503)])
        self.assertEqual(len(records), 1)
        self.assertEqual(provider.status, 'failed')

    def test_upstream_failure(self):
        provider = self.provider()
        self.run_pages(provider, [response({'results': [], 'unresponsive_engines': [['bing', 'timeout']]})])
        self.assertEqual(provider.status, 'partial')

    def test_page_cap(self):
        provider = self.provider(max_pages=1)
        _, calls = self.run_pages(provider, [response({'results': [result()]})])
        self.assertEqual(len(calls), 1)
        self.assertEqual(provider.status, 'limited')

    def test_csv_quotes(self):
        provider = self.provider()
        record = provider.parse_result(result('Jane Doe - Engineer, "Platform" | LinkedIn'))
        with patch('crosslinked.search.csv.info') as log:
            provider.log_results(record)
        row = next(csv.reader(io.StringIO(log.call_args.args[0])))
        self.assertEqual(len(row), 6)
        self.assertEqual(row[3], 'Engineer, "Platform"')

    def test_cli_validation(self):
        for flags in (['--search', 'unknown'], ['--search', 'searxng'], ['-t', 'nan'], ['-j', '-1']):
            with patch.dict('os.environ', {}, clear=True), patch('sys.argv', ['crosslinked', 'Example', '-f', '{first}.{last}'] + flags):
                with self.assertRaises(SystemExit) as exc:
                    cli()
                self.assertEqual(exc.exception.code, 2)


if __name__ == '__main__':
    unittest.main()

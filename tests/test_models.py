import unittest

from crosslinked.models import (COMPLETE, FAILED, LIMITED, PARTIAL, Candidate, ProviderState,
                                ReviewedCandidate, RunState)


class CandidateTests(unittest.TestCase):
    def test_roundtrip(self):
        candidate = Candidate(name='jane doe', title='Engineer', url='https://www.linkedin.com/in/jane',
                              text='Jane Doe - Engineer', snippet='s', engines='google', observed_at='t', provider='searxng')
        self.assertEqual(Candidate.from_dict(candidate.to_dict()), candidate)
        self.assertEqual(list(candidate.to_dict()), ['name', 'title', 'url', 'text', 'snippet', 'engines', 'observed_at', 'provider'])

    def test_legacy_csv_headers(self):
        row = {'Datetime': '09-05-2026 10:00:00', 'Search': 'google', 'Name': ' jane doe ', 'Title': 'Engineer',
               'URL': 'https://www.linkedin.com/in/jane', 'rawText': 'Jane Doe - Engineer', 'extra': 'ignored'}
        candidate = Candidate.from_dict(row)
        self.assertEqual(candidate, Candidate(name='jane doe', title='Engineer', url='https://www.linkedin.com/in/jane',
                                              text='Jane Doe - Engineer', observed_at='09-05-2026 10:00:00', provider='google'))

    def test_review_row_prefers_original_name(self):
        row = {'original_name': 'Dr Jane Doe', 'name': 'jane doe', 'classification': 'uncertain'}
        self.assertEqual(Candidate.from_dict(row).name, 'Dr Jane Doe')
        self.assertEqual(Candidate.from_dict({'name': 'jane doe'}).title, 'N/A')

    def test_unusable_input(self):
        for data in ({}, {'name': '  '}, {'Name': None}, 'jane', None, {'title': 'x'}):
            self.assertIsNone(Candidate.from_dict(data))

    def test_identity(self):
        self.assertEqual(Candidate(name='a', url='u').identity, 'u')
        self.assertNotEqual(Candidate(name='a', text='x').identity, Candidate(name='a', text='y').identity)

    def test_reviewed_dict_order(self):
        reviewed = ReviewedCandidate(name='jane doe', original_name='Jane Doe', classification='non_person', reason='r')
        keys = list(reviewed.to_dict())
        self.assertEqual(keys[:3], ['original_name', 'name', 'classification'])
        self.assertEqual(keys[-1], 'provider')
        self.assertEqual(reviewed.evidence_status, 'unverified search evidence')


class StateTests(unittest.TestCase):
    def test_provider_state_warn_once_and_finish(self):
        state = ProviderState('searxng')
        self.assertTrue(state.warn('x'))
        self.assertFalse(state.warn('x'))
        self.assertEqual(state.warnings, ['x'])
        state.finish(FAILED, 'request_failure')
        self.assertFalse(state.successful)
        with self.assertRaises(ValueError):
            state.finish('broken', 'x')
        self.assertEqual(state.to_dict()['stop_reason'], 'request_failure')

    def test_run_status_is_worst_provider(self):
        run = RunState(target='Example', mode='search')
        self.assertEqual(run.status, COMPLETE)
        self.assertEqual(run.exit_code, 0)
        run.providers.append(ProviderState('google', status=LIMITED, stop_reason='time_budget'))
        self.assertEqual(run.status, LIMITED)
        self.assertEqual(run.exit_code, 0)
        run.providers.append(ProviderState('searxng', status=PARTIAL, stop_reason='page_limit'))
        self.assertEqual(run.status, PARTIAL)
        self.assertEqual(run.exit_code, 1)
        run.providers.append(ProviderState('bing', status=FAILED, stop_reason='http_429'))
        self.assertEqual(run.status, FAILED)
        data = run.to_dict()
        self.assertEqual(data['schema_version'], 1)
        self.assertEqual(data['status'], FAILED)
        self.assertEqual(data['exit_code'], 1)
        self.assertEqual([p['provider'] for p in data['providers']], ['google', 'searxng', 'bing'])

    def test_interrupted_run_is_limited(self):
        run = RunState(target='Example', mode='search', interrupted=True)
        self.assertEqual(run.status, LIMITED)
        run.providers.append(ProviderState('google', status=FAILED))
        self.assertEqual(run.status, FAILED)

    def test_classification_counts(self):
        run = RunState(target='x', mode='parse')
        counts = run.count_classifications([ReviewedCandidate(name='a', classification='uncertain'),
                                            ReviewedCandidate(name='b', classification='uncertain'),
                                            ReviewedCandidate(name='c', classification='non_person')])
        self.assertEqual(counts, {'uncertain': 2, 'non_person': 1})
        self.assertEqual(run.to_dict()['classification'], counts)


if __name__ == '__main__':
    unittest.main()

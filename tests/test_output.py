import csv
import json
import tempfile
import unittest
from pathlib import Path

from crosslinked.models import Candidate, ProviderState, ReviewedCandidate, RunState
from crosslinked.output import (RawCsvWriter, is_input_file, read_records, write_jsonl, write_review,
                                write_run_state, write_txt)


def candidates():
    return [Candidate(name='jane doe', title='Engineer, "Platform"', url='https://www.linkedin.com/in/jane',
                      text='Jane Doe - Engineer, "Platform"', observed_at='2026-09-05T10:00:00+00:00', provider='searxng'),
            Candidate(name='josé nuñez', url='https://www.linkedin.com/in/jose', text='José Nuñez – Student', provider='google')]


class OutputTests(unittest.TestCase):
    def test_input_detection(self):
        self.assertTrue(is_input_file('names.csv'))
        self.assertTrue(is_input_file('run.JSONL'))
        self.assertFalse(is_input_file('Example Company'))
        self.assertFalse(is_input_file('csv'))

    def test_jsonl_roundtrip_unicode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory, 'out.jsonl'))
            self.assertEqual(write_jsonl(path, candidates()), 2)
            lines = Path(path).read_text(encoding='utf-8').splitlines()
            self.assertEqual(len(lines), 2)
            self.assertIn('josé nuñez', lines[1])
            self.assertEqual(json.loads(lines[0])['provider'], 'searxng')
            self.assertEqual(read_records(path), candidates())

    def test_jsonl_skips_blank_lines_and_rejects_garbage(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, 'in.jsonl')
            path.write_text('\n{"name": "jane doe"}\n\n{"title": "no name"}\n', encoding='utf-8')
            self.assertEqual([r.name for r in read_records(str(path))], ['jane doe'])
            path.write_text('{"name": "jane doe"}\nnot json\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'line 2'):
                read_records(str(path))

    def test_raw_csv_appends_with_single_header(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory, 'raw.csv'))
            first, second = candidates()
            writer = RawCsvWriter(path)
            writer(first)
            writer.close()
            writer = RawCsvWriter(path)
            writer(second)
            writer.close()
            with open(path, newline='', encoding='utf-8') as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([r['Name'] for r in rows], ['jane doe', 'josé nuñez'])
            self.assertEqual(rows[0]['Search'], 'searxng')
            self.assertEqual(rows[0]['Title'], 'Engineer, "Platform"')
            self.assertEqual(read_records(path), candidates())

    def test_review_csv_readable_as_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory, 'x.review.csv'))
            reviewed = ReviewedCandidate(name='jane doe', original_name='Dr Jane Doe', classification='uncertain',
                                         reason='r', url='https://www.linkedin.com/in/jane', provider='searxng')
            write_review(path, [reviewed])
            records = read_records(path)
            self.assertEqual(records[0].name, 'Dr Jane Doe')
            self.assertEqual(records[0].provider, 'searxng')
            Path(directory, 'bad.csv').write_text('Title,URL\nx,y\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Name'):
                read_records(str(Path(directory, 'bad.csv')))

    def test_txt_and_run_state(self):
        with tempfile.TemporaryDirectory() as directory:
            txt = Path(directory, 'names.txt')
            write_txt(str(txt), ['jane.doe', 'josé.nuñez'])
            self.assertEqual(txt.read_text(encoding='utf-8'), 'jane.doe\njosé.nuñez\n')
            write_txt(str(txt), [])
            self.assertEqual(txt.read_text(encoding='utf-8'), '')
            run = RunState(target='Example', mode='search', providers=[ProviderState('searxng', status='partial')])
            summary = Path(directory, 'names.run.json')
            write_run_state(str(summary), run)
            data = json.loads(summary.read_text(encoding='utf-8'))
            self.assertEqual(data['status'], 'partial')
            self.assertEqual(data['exit_code'], 1)
            self.assertEqual(data['providers'][0]['provider'], 'searxng')


if __name__ == '__main__':
    unittest.main()

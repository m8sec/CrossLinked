"""Exercise actual HTTP, CLI exit codes, and output files against a local fixture."""
import csv
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Thread
import unittest
from urllib.parse import parse_qs, urlsplit


class CliIntegrationTests(unittest.TestCase):
    def test_offline_review_and_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, 'source.csv')
            with source.open('w', encoding='utf-8', newline='') as handle:
                writer = csv.writer(handle)
                writer.writerow(['Datetime', 'Search', 'Name', 'Title', 'URL', 'rawText'])
                for name, role in [('Dr Jane Example', 'Lecturer at Example University'),
                                   ('Sam Example', 'Student at Example University'),
                                   ('Al Example', 'Graduate from Example University'),
                                   ('Jo Example', 'Example University'),
                                   ('Jane B.', 'Lecturer at Example University')]:
                    writer.writerow(['2026', 'searxng', name, role, '', name + ' - ' + role])
            before = source.read_bytes()
            command = [sys.executable, str(Path(__file__).resolve().parents[1] / 'crosslinked.py'),
                       'source.csv', '--organization', 'Example University', '-f', '{first}.{last}', '-o', 'reviewed']
            run = subprocess.run(command, cwd=directory, capture_output=True, text=True, timeout=15)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertEqual(Path(directory, 'reviewed.txt').read_text().splitlines(), ['jane.example', 'sam.example'])
            self.assertFalse(Path(directory, 'reviewed.csv').exists())
            with Path(directory, 'reviewed.review.csv').open(encoding='utf-8', newline='') as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 5)
            self.assertEqual(rows[0]['original_name'], 'Dr Jane Example')
            self.assertTrue(rows[-1]['name_issue'])
            self.assertEqual(source.read_bytes(), before)
            with Path(directory, 'reviewed.jsonl').open(encoding='utf-8') as handle:
                records = [json.loads(line) for line in handle]
            self.assertEqual([r['classification'] for r in records][:2], ['current_staff_candidate', 'current_student_candidate'])
            self.assertEqual(records[0]['provider'], 'searxng')
            summary = json.loads(Path(directory, 'reviewed.run.json').read_text(encoding='utf-8'))
            self.assertEqual(summary['mode'], 'parse')
            self.assertEqual(summary['status'], 'complete')
            self.assertEqual(summary['candidates'], 5)
            self.assertEqual(summary['selected'], 2)
            self.assertEqual(summary['classification']['uncertain'], 1)
            self.assertEqual(summary['providers'], [])
            run = subprocess.run(command + ['--include-uncertain'], cwd=directory, capture_output=True, text=True, timeout=15)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn('jo.example', Path(directory, 'reviewed.txt').read_text().splitlines())
            # The JSONL export is itself a valid input for a second pass.
            command = [sys.executable, str(Path(__file__).resolve().parents[1] / 'crosslinked.py'),
                       'reviewed.jsonl', '--organization', 'Example University', '-f', '{f}{last}', '-o', 'second']
            run = subprocess.run(command, cwd=directory, capture_output=True, text=True, timeout=15)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertEqual(Path(directory, 'second.txt').read_text().splitlines(), ['jexample', 'sexample'])
            run = subprocess.run(command[:-2] + ['-o', 'reviewed'], cwd=directory, capture_output=True, text=True, timeout=15)
            self.assertEqual(run.returncode, 2)
            self.assertIn('overwrite', run.stderr)

    def test_http_to_files_and_failure_exit(self):
        pages = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                params = parse_qs(urlsplit(self.path).query)
                pages.append(params)
                if 'Failure' in params['q'][0]:
                    self.send_response(403)
                    self.end_headers()
                    return
                payload = {'results': []}
                if params['pageno'] == ['1']:
                    payload['results'] = [{'url': 'https://www.linkedin.com/in/jane-example',
                                           'title': 'Jane Example - Engineer at Example | LinkedIn'}]
                body = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                command = [sys.executable, str(Path(__file__).resolve().parents[1] / 'crosslinked.py'),
                           '--search', 'searxng', '--searxng-url',
                           'http://127.0.0.1:{}'.format(server.server_port),
                           '-j', '0', '-f', '{first}.{last}@example.com']
                run = subprocess.run(command + ['Example'], cwd=directory, capture_output=True, text=True, timeout=15)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                self.assertEqual(Path(directory, 'names.txt').read_text().strip(), 'jane.example@example.com')
                with Path(directory, 'names.csv').open(newline='') as handle:
                    rows = list(csv.DictReader(handle))
                self.assertEqual(rows[0]['Search'], 'searxng')
                self.assertEqual(rows[0]['Name'], 'jane example')
                self.assertEqual([p['pageno'] for p in pages], [['1'], ['2']])
                summary = json.loads(Path(directory, 'names.run.json').read_text(encoding='utf-8'))
                self.assertEqual(summary['mode'], 'search')
                self.assertEqual(summary['status'], 'complete')
                self.assertEqual(summary['exit_code'], 0)
                self.assertEqual(summary['providers'][0]['stop_reason'], 'empty_page')
                self.assertEqual(summary['providers'][0]['pages'], 2)
                self.assertEqual(summary['providers'][0]['records'], 1)
                self.assertEqual(sorted(summary['outputs']), ['jsonl', 'raw_csv', 'review_csv', 'run_json', 'txt'])
                self.assertEqual(json.loads(Path(directory, 'names.jsonl').read_text(encoding='utf-8'))['url'],
                                 'https://www.linkedin.com/in/jane-example')
                run = subprocess.run(command + ['Failure'], cwd=directory, capture_output=True, text=True, timeout=15)
                self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
                self.assertIn('HTTP 403', run.stdout)
                self.assertNotIn('No results found', run.stdout)
                summary = json.loads(Path(directory, 'names.run.json').read_text(encoding='utf-8'))
                self.assertEqual(summary['status'], 'failed')
                self.assertEqual(summary['providers'][0]['stop_reason'], 'request_failure')
                self.assertTrue(summary['providers'][0]['warnings'])
                self.assertEqual(Path(directory, 'names.txt').read_text(), '')
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

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
                                           'title': 'Jane Example - Engineer | LinkedIn'}]
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
                run = subprocess.run(command + ['Failure'], cwd=directory, capture_output=True, text=True, timeout=15)
                self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
                self.assertIn('HTTP 403', run.stdout)
                self.assertNotIn('No results found', run.stdout)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

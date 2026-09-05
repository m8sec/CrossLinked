"""SearXNG JSON provider. No LinkedIn requests or browser required."""
import re
from time import monotonic, sleep
from urllib.parse import urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup
from unidecode import unidecode

from crosslinked.search import CrossLinked, get_proxy
from crosslinked.logger import Log


def search_endpoint(value):
    parts = urlsplit(value)
    if (parts.scheme not in ('http', 'https') or not parts.hostname
            or parts.username or parts.password or parts.query or parts.fragment):
        raise ValueError('SearXNG URL must be an HTTP(S) URL without credentials, query or fragment')
    path = parts.path.rstrip('/')
    if not path.endswith('/search'):
        path += '/search'
    return urlunsplit((parts.scheme, parts.netloc, path, '', ''))


class SearXNG(CrossLinked):
    def __init__(self, target, endpoint, timeout=15, jitter=1, max_pages=5, proxies=None):
        super().__init__('searxng', target, timeout, proxies=proxies or [], jitter=jitter)
        self.endpoint = search_endpoint(endpoint)
        self.max_pages = max_pages
        self.status = 'pending'
        self.warnings = []

    def warn(self, message):
        self.warnings.append(message)
        Log.warn(message)

    def parse_result(self, item):
        if not isinstance(item, dict):
            return None
        url, title = item.get('url'), item.get('title')
        if not isinstance(url, str) or not isinstance(title, str):
            return None
        try:
            parts = urlsplit(url)
            host = (parts.hostname or '').lower()
        except ValueError:
            return None
        if (parts.scheme not in ('http', 'https') or parts.username or parts.password
                or not (host == 'linkedin.com' or host.endswith('.linkedin.com'))
                or not re.fullmatch(r'/in/[^/]+/?', parts.path)):
            return None
        text = BeautifulSoup(title, 'html.parser').get_text(' ', strip=True)
        text = re.sub(r'\s+', ' ', text).strip()
        fields = re.split(r'\s+[-–—|]\s+', text)
        name = fields[0].strip()
        if len(name.split()) < 2 or 'linkedin' in name.lower() or not any(c.isalpha() for c in name):
            return None
        return {'name': unidecode(name).lower(),
                'title': fields[1] if len(fields) > 1 and fields[1].lower() != 'linkedin' else 'N/A',
                'url': 'https://www.linkedin.com' + parts.path.rstrip('/'),
                'text': text}

    def search(self):
        deadline = monotonic() + self.timeout
        seen_urls, seen_pages = set(), set()
        self.status = 'complete'
        with requests.Session() as session:
            for page in range(1, self.max_pages + 1):
                remaining = deadline - monotonic()
                if remaining <= 0:
                    self.status = 'limited'
                    break
                try:
                    response = session.get(self.endpoint, params={
                        'q': 'site:linkedin.com/in "{}"'.format(self.target.replace('"', ' ')),
                        'format': 'json', 'pageno': page, 'categories': 'general'},
                        timeout=min(remaining, 15), proxies=get_proxy(self.proxies))
                    if response.status_code == 403:
                        raise ValueError('HTTP 403: enable JSON in SearXNG search.formats and check instance access')
                    response.raise_for_status()
                    payload = response.json()
                    if not isinstance(payload, dict) or not isinstance(payload.get('results'), list):
                        raise ValueError('Invalid SearXNG JSON: expected a results list')
                except (requests.RequestException, ValueError) as exc:
                    self.status = 'failed'
                    self.warn('SearXNG request failed: {}'.format(exc))
                    break
                if payload.get('unresponsive_engines'):
                    self.status = 'partial'
                    self.warn('SearXNG upstream failures: {}'.format(payload['unresponsive_engines']))
                items = payload['results']
                if not items:
                    break
                fingerprint = repr(items)
                if fingerprint in seen_pages:
                    self.status = 'limited' if self.status == 'complete' else self.status
                    self.warn('SearXNG repeated a page; stopping pagination')
                    break
                seen_pages.add(fingerprint)
                for item in items:
                    record = self.parse_result(item)
                    if record and record['url'] not in seen_urls:
                        seen_urls.add(record['url'])
                        self.log_results(record)
                Log.info('SearXNG page {}: {} unique profiles'.format(page, len(self.results)))
                if page == self.max_pages:
                    self.status = 'limited' if self.status == 'complete' else self.status
                else:
                    sleep(min(self.jitter, max(0, deadline - monotonic())))
        Log.info('SearXNG status: {}'.format(self.status))
        return self.results

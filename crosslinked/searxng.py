"""SearXNG JSON provider. No LinkedIn requests or browser required."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from time import monotonic, sleep
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup
from unidecode import unidecode

from crosslinked.logger import Log
from crosslinked.models import COMPLETE, FAILED, LIMITED, PARTIAL, Candidate
from crosslinked.provider import Provider
from crosslinked.search import get_proxy


def search_endpoint(value: str) -> str:
    parts = urlsplit(value)
    if (parts.scheme not in ('http', 'https') or not parts.hostname
            or parts.username or parts.password or parts.query or parts.fragment):
        raise ValueError('SearXNG URL must be an HTTP(S) URL without credentials, query or fragment')
    path = parts.path.rstrip('/')
    if not path.endswith('/search'):
        path += '/search'
    return urlunsplit((parts.scheme, parts.netloc, path, '', ''))


class SearXNG(Provider):
    name = 'searxng'

    def __init__(self, target: str, endpoint: str, timeout: float = 15, jitter: float = 1, max_pages: int = 5,
                 proxies: Optional[Sequence[str]] = None, engines: Optional[Sequence[str]] = None,
                 cache_dir: Optional[str] = None, resume: bool = False, request_timeout: float = 30,
                 retries: int = 0):
        super().__init__(target, timeout, jitter, proxies)
        self.endpoint = search_endpoint(endpoint)
        self.max_pages = max_pages
        self.engines = list(engines or [])
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.resume = resume
        self.request_timeout = request_timeout
        self.retries = retries

    def validate(self) -> None:
        self.validate_engines()

    def validate_engines(self) -> None:
        """Fail closed: unknown names may silently fall back to default engines."""
        if not self.engines:
            return
        response = requests.get(self.endpoint.rsplit('/search', 1)[0] + '/config',
                                timeout=min(self.timeout, self.request_timeout), proxies=get_proxy(self.proxies))
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get('engines'), list):
            raise ValueError('Instance /config did not return an engine list')
        available = {item.get('name') for item in payload['engines'] if isinstance(item, dict)}
        unknown = set(self.engines) - available
        if unknown:
            raise ValueError('Unknown SearXNG engines: ' + ', '.join(sorted(unknown)))

    def request_page(self, session, params, remaining):
        deadline = monotonic() + remaining
        for attempt in range(self.retries + 1):
            budget = deadline - monotonic()
            if budget <= 0:
                raise requests.Timeout('Search time budget exhausted before request/retry')
            try:
                response = session.get(self.endpoint, params=params,
                                       timeout=min(budget, self.request_timeout), proxies=get_proxy(self.proxies))
                if response.status_code not in (502, 503, 504):
                    return response
                response.raise_for_status()
            except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as exc:
                if attempt == self.retries:
                    raise
                delay = 2 ** (attempt + 1)
                if isinstance(exc, requests.HTTPError) and exc.response is not None:
                    retry_after = exc.response.headers.get('Retry-After')
                    if retry_after:
                        # Unparseable/date headers are not retried rather than
                        # risk retrying before the server's requested time.
                        if not retry_after.isdigit():
                            raise
                        delay = max(delay, int(retry_after))
                if delay >= deadline - monotonic():
                    raise
                self.warn('Temporary request failure; retry {}/{} in {} seconds'.format(attempt + 1, self.retries, delay))
                sleep(delay)

    def cache_path(self, page: int) -> Path:
        if not self.cache_dir:
            raise ValueError('No cache directory configured')
        identity = json.dumps([self.endpoint, self.target, sorted(self.engines), page, 2])
        return self.cache_dir / (hashlib.sha256(identity.encode()).hexdigest() + '.json')

    def load_page(self, page: int) -> Optional[Dict[str, Any]]:
        if not self.cache_dir or not self.resume:
            return None
        path = self.cache_path(page)
        if not path.exists():
            return None
        try:
            saved = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(saved, dict) or not isinstance(saved.get('payload'), dict):
                raise ValueError('invalid cache envelope')
            payload = saved['payload']
            if not isinstance(payload.get('results'), list):
                raise ValueError('invalid cached results')
            return saved
        except (OSError, ValueError) as exc:
            self.warn('Ignoring invalid page cache: {}'.format(exc))
            return None

    def save_page(self, page: int, payload: Dict[str, Any]) -> None:
        if not self.cache_dir:
            return
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path = self.cache_path(page)
        retained: Dict[str, Dict[str, Any]] = {}
        if path.exists():
            try:
                previous = json.loads(path.read_text(encoding='utf-8'))
                for record in previous.get('retained_records', []):
                    if isinstance(record, dict) and record.get('url'):
                        retained[record['url']] = record
                for item in previous.get('payload', {}).get('results', []):
                    candidate = self.parse_result(item)
                    if candidate:
                        candidate.observed_at = previous.get('observed_at', '')
                        retained.setdefault(candidate.url, candidate.to_dict())
            except (OSError, ValueError, AttributeError, TypeError):
                pass
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps({'observed_at': self.runtime, 'payload': payload,
                                        'retained_records': list(retained.values())}, ensure_ascii=False), encoding='utf-8')
        os.replace(temporary, path)

    def parse_result(self, item: Any) -> Optional[Candidate]:
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
        content = item.get('content') or ''
        engines = item.get('engines')
        return Candidate(
            name=unidecode(name).lower(),
            title=fields[1] if len(fields) > 1 and fields[1].lower() != 'linkedin' else 'N/A',
            url='https://www.linkedin.com' + parts.path.rstrip('/'),
            text=text,
            snippet=BeautifulSoup(content, 'html.parser').get_text(' ', strip=True) if isinstance(content, str) else '',
            engines=','.join(str(e) for e in engines) if isinstance(engines, list) else str(item.get('engine', '')),
            observed_at=self.runtime,
            provider=self.name)

    def _retained(self, saved: Dict[str, Any]) -> List[Candidate]:
        records = []
        for record in saved.get('retained_records', []):
            if isinstance(record, dict) and all(isinstance(record.get(k), str) for k in ('name', 'title', 'url', 'text')):
                candidate = Candidate.from_dict(record)
                if candidate:
                    records.append(candidate)
        return records

    def search(self) -> List[Candidate]:
        deadline = monotonic() + self.timeout
        seen_pages = set()
        self.state.finish(COMPLETE, 'page_limit')
        with requests.Session() as session:
            for page in range(1, self.max_pages + 1):
                remaining = deadline - monotonic()
                if remaining <= 0:
                    self.state.finish(LIMITED, 'time_budget')
                    break
                saved = self.load_page(page)
                if saved:
                    for record in self._retained(saved):
                        self.add_result(record)
                # A partial cached page is evidence to preserve, not evidence
                # that this page is complete. Retry it on resume.
                if saved and saved['payload'].get('unresponsive_engines'):
                    for item in saved['payload']['results']:
                        retried = self.parse_result(item)
                        if retried:
                            retried.observed_at = saved.get('observed_at', '')
                            self.add_result(retried)
                    saved = None
                try:
                    params: Dict[str, Any] = {
                        'q': 'site:linkedin.com/in "{}"'.format(self.target.replace('"', ' ')),
                        'format': 'json', 'pageno': page}
                    if self.engines:
                        params['engines'] = ','.join(self.engines)
                    else:
                        params['categories'] = 'general'
                    if saved:
                        payload = saved['payload']
                        Log.info('SearXNG page {}: using saved response'.format(page))
                    else:
                        response = self.request_page(session, params, remaining)
                        if response.status_code == 403:
                            raise ValueError('HTTP 403: enable JSON in SearXNG search.formats and check instance access')
                        response.raise_for_status()
                        payload = response.json()
                    if not isinstance(payload, dict) or not isinstance(payload.get('results'), list):
                        raise ValueError('Invalid SearXNG JSON: expected a results list')
                    if not saved:
                        try:
                            self.save_page(page, payload)
                        except OSError as exc:
                            self.warn('Could not save page progress: {}'.format(exc))
                except (requests.RequestException, ValueError) as exc:
                    self.state.finish(FAILED, 'request_failure')
                    self.warn('SearXNG request failed: {}'.format(exc))
                    break
                self.state.pages += 1
                if payload.get('unresponsive_engines'):
                    self.status = PARTIAL
                    for failure in payload['unresponsive_engines']:
                        if isinstance(failure, (list, tuple)) and len(failure) >= 2:
                            engine, reason = str(failure[0]), str(failure[1])
                            if engine not in self.engine_failures:
                                self.warn('SearXNG engine {} failed: {}'.format(engine, reason))
                            self.engine_failures[engine] = reason
                items = payload['results']
                Log.info('SearXNG page {}: {} raw results'.format(page, len(items)))
                if not items:
                    self.stop_reason = 'empty_page_with_engine_failures' if payload.get('unresponsive_engines') else 'empty_page'
                    break
                fingerprint = repr(items)
                if fingerprint in seen_pages:
                    self.stop_reason = 'repeated_page'
                    self.status = LIMITED if self.status == COMPLETE else self.status
                    self.warn('SearXNG repeated a page; stopping pagination')
                    break
                seen_pages.add(fingerprint)
                for item in items:
                    parsed = self.parse_result(item)
                    if parsed:
                        if saved:
                            parsed.observed_at = saved.get('observed_at', '')
                        self.add_result(parsed)
                Log.info('SearXNG page {}: {} unique profiles'.format(page, len(self.results)))
                if page == self.max_pages:
                    self.status = LIMITED if self.status == COMPLETE else self.status
                elif not saved:
                    sleep(min(self.jitter, max(0, deadline - monotonic())))
        Log.info('SearXNG status: {}; stopped: {}'.format(self.status, self.stop_reason))
        if self.engine_failures:
            Log.warn('Affected engines: ' + ', '.join(sorted(self.engine_failures)))
        return self.results

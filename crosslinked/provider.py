"""Common provider interface: every search backend yields Candidates and a ProviderState."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional, Sequence, Set

import requests

from crosslinked.logger import Log
from crosslinked.models import FAILED, Candidate, ProviderState, now_iso

Sink = Callable[[Candidate], None]


class Provider(ABC):
    """Base class for search providers.

    Subclasses implement search() and report progress through self.state.
    Results are de-duplicated by profile URL as they arrive and streamed to any
    registered sinks (for example the raw CSV writer) so partial runs keep
    their evidence.
    """
    name = 'provider'

    def __init__(self, target: str, timeout: float = 15, jitter: float = 1,
                 proxies: Optional[Sequence[str]] = None, name: Optional[str] = None):
        if name:
            self.name = name
        self.target = target
        self.timeout = float(timeout)
        self.jitter = float(jitter)
        self.proxies = list(proxies or [])
        self.runtime = now_iso()
        self.results: List[Candidate] = []
        self.state = ProviderState(provider=self.name)
        self.sinks: List[Sink] = []
        self._seen: Set[str] = set()

    # Convenience views over the state object.
    @property
    def status(self) -> str:
        return self.state.status

    @status.setter
    def status(self, value: str) -> None:
        self.state.status = value

    @property
    def stop_reason(self) -> str:
        return self.state.stop_reason

    @stop_reason.setter
    def stop_reason(self, value: str) -> None:
        self.state.stop_reason = value

    @property
    def warnings(self) -> List[str]:
        return self.state.warnings

    @property
    def engine_failures(self) -> Dict[str, str]:
        return self.state.engine_failures

    def warn(self, message: str) -> None:
        if self.state.warn(message):
            Log.warn(message)

    def validate(self) -> None:
        """Check configuration before searching. Raise ValueError or a requests error to abort."""
        return None

    @abstractmethod
    def search(self) -> List[Candidate]:
        """Collect candidates, update self.state, and return self.results."""

    def run(self) -> List[Candidate]:
        """Validate then search, always leaving a finished ProviderState."""
        self.state.started_at = now_iso()
        try:
            self.validate()
        except (ValueError, requests.RequestException) as exc:
            self.warn('{} validation failed: {}'.format(self.name, exc))
            self.state.finish(FAILED, 'validation_failed')
            self.state.finished_at = now_iso()
            return []
        try:
            return self.search()
        finally:
            self.state.records = len(self.results)
            self.state.finished_at = now_iso()

    def add_result(self, candidate: Candidate) -> bool:
        """Keep a new candidate; returns False for duplicates and non-profile noise."""
        if not candidate.name or 'linkedin.com' in candidate.name:
            return False
        if candidate.identity in self._seen:
            return False
        if not candidate.provider:
            candidate.provider = self.name
        if not candidate.observed_at:
            candidate.observed_at = self.runtime
        self._seen.add(candidate.identity)
        self.results.append(candidate)
        self.state.records = len(self.results)
        logging.debug('name: {:25} RawTxt: {}'.format(candidate.name, candidate.text))
        for sink in self.sinks:
            sink(candidate)
        return True

    # Name kept from the previous API.
    log_results = add_result

"""Typed records shared by providers, the reviewer, and output writers."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional

SCHEMA_VERSION = 1

# Provider and run statuses, ordered from best to worst.
PENDING = 'pending'
COMPLETE = 'complete'
LIMITED = 'limited'
PARTIAL = 'partial'
FAILED = 'failed'
STATUSES = (PENDING, COMPLETE, LIMITED, PARTIAL, FAILED)
# A run is unsuccessful when any provider stopped because of a failure or lost
# part of its upstream coverage.
UNSUCCESSFUL = (PARTIAL, FAILED)


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec='seconds')


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ''


# Legacy raw CSV headers and review/JSONL keys, in order of preference.
CANDIDATE_ALIASES = {
    'name': ('Name', 'original_name', 'name'),
    'title': ('Title', 'title'),
    'url': ('URL', 'url'),
    'text': ('rawText', 'text'),
    'snippet': ('snippet',),
    'engines': ('engines',),
    'observed_at': ('Datetime', 'observed_at'),
    'provider': ('Search', 'provider'),
}


@dataclass
class Candidate:
    """One search result that looks like a LinkedIn profile. Nothing is verified."""
    name: str
    title: str = 'N/A'
    url: str = ''
    text: str = ''
    snippet: str = ''
    engines: str = ''
    observed_at: str = ''
    provider: str = ''

    @property
    def identity(self) -> str:
        """Key used for de-duplication within a run: the profile URL when known."""
        return self.url or '{}\n{}'.format(self.name, self.text)

    def to_dict(self) -> Dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in fields(Candidate)}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Optional['Candidate']:
        """Build from a raw CSV row, a review row, a JSONL record or a plain dict.

        Returns None when no usable name is present. Unknown keys are ignored.
        """
        if not isinstance(data, Mapping):
            return None
        values: Dict[str, str] = {}
        for attr, keys in CANDIDATE_ALIASES.items():
            for key in keys:
                text = _text(data.get(key))
                if text:
                    values[attr] = text
                    break
        if not values.get('name'):
            return None
        values.setdefault('title', 'N/A')
        return cls(**values)


REVIEW_FIELDS = ('original_name', 'name', 'classification', 'reason', 'name_issue',
                 'evidence_status', 'title', 'url', 'text', 'snippet', 'engines',
                 'observed_at', 'provider')


@dataclass
class ReviewedCandidate(Candidate):
    """A candidate with an explainable, unverified affiliation classification."""
    original_name: str = ''
    classification: str = 'uncertain'
    reason: str = ''
    name_issue: str = ''
    evidence_status: str = 'unverified search evidence'

    def to_dict(self) -> Dict[str, Any]:
        return {key: getattr(self, key) for key in REVIEW_FIELDS}


@dataclass
class ProviderState:
    """Outcome of one provider within a run."""
    provider: str
    status: str = PENDING
    stop_reason: str = 'not_started'
    warnings: List[str] = field(default_factory=list)
    engine_failures: Dict[str, str] = field(default_factory=dict)
    pages: int = 0
    records: int = 0
    started_at: str = ''
    finished_at: str = ''

    def warn(self, message: str) -> bool:
        """Record a warning once; returns True when it is new."""
        if message in self.warnings:
            return False
        self.warnings.append(message)
        return True

    def finish(self, status: str, stop_reason: str) -> None:
        if status not in STATUSES:
            raise ValueError('Unknown provider status: {}'.format(status))
        self.status = status
        self.stop_reason = stop_reason

    @property
    def successful(self) -> bool:
        return self.status not in UNSUCCESSFUL

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RunState:
    """Outcome of one CLI invocation, aggregated from its providers."""
    target: str
    mode: str  # 'search' or 'parse'
    started_at: str = field(default_factory=now_iso)
    finished_at: str = ''
    source: str = ''
    organization: str = ''
    providers: List[ProviderState] = field(default_factory=list)
    candidates: int = 0
    selected: int = 0
    classification: Dict[str, int] = field(default_factory=dict)
    outputs: Dict[str, str] = field(default_factory=dict)
    interrupted: bool = False

    @property
    def status(self) -> str:
        """Worst provider status; a run without providers is complete."""
        worst = max((p.status for p in self.providers), key=STATUSES.index, default=COMPLETE)
        if self.interrupted and worst in (PENDING, COMPLETE):
            return LIMITED
        return worst

    @property
    def exit_code(self) -> int:
        return 1 if self.status in UNSUCCESSFUL else 0

    def count_classifications(self, records: Iterable[ReviewedCandidate]) -> Dict[str, int]:
        self.classification = dict(Counter(r.classification for r in records))
        return self.classification

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data.update(schema_version=SCHEMA_VERSION, status=self.status, exit_code=self.exit_code)
        return data

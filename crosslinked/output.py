"""Readers and writers for run outputs: raw CSV, JSONL, TXT, review CSV, run summary."""
from __future__ import annotations

import csv
import json
import os
from typing import Iterable, List, Sequence

from crosslinked.models import REVIEW_FIELDS, Candidate, RunState

RAW_FIELDS = ('Datetime', 'Search', 'Name', 'Title', 'URL', 'rawText')
INPUT_SUFFIXES = ('.csv', '.jsonl')


def is_input_file(value: str) -> bool:
    return value.lower().endswith(INPUT_SUFFIXES)


def raw_row(candidate: Candidate) -> List[str]:
    return [candidate.observed_at, candidate.provider, candidate.name,
            candidate.title, candidate.url, candidate.text]


class RawCsvWriter:
    """Append-only evidence log, flushed per record so interrupted runs keep data."""

    def __init__(self, path: str):
        self.path = path
        empty = not os.path.exists(path) or os.path.getsize(path) == 0
        self.handle = open(path, 'a', encoding='utf-8', newline='')
        self.writer = csv.writer(self.handle)
        if empty:
            self.writer.writerow(RAW_FIELDS)
            self.handle.flush()

    def __call__(self, candidate: Candidate) -> None:
        self.writer.writerow(raw_row(candidate))
        self.handle.flush()

    def close(self) -> None:
        self.handle.close()


def write_txt(path: str, names: Iterable[str]) -> None:
    with open(path, 'w', encoding='utf-8') as handle:
        for name in names:
            handle.write(name + '\n')


def write_jsonl(path: str, records: Sequence[Candidate]) -> int:
    with open(path, 'w', encoding='utf-8') as handle:
        for record in records:
            handle.write(json.dumps(record.to_dict(), ensure_ascii=False) + '\n')
    return len(records)


def write_review(path: str, records: Iterable[Candidate]) -> None:
    with open(path, 'w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(REVIEW_FIELDS), extrasaction='ignore')
        writer.writeheader()
        writer.writerows(r.to_dict() for r in records)


def write_run_state(path: str, run: RunState) -> None:
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(run.to_dict(), handle, indent=2, ensure_ascii=False)
        handle.write('\n')


def read_records(path: str) -> List[Candidate]:
    """Load candidates from a raw CSV, a review CSV, or a JSONL export."""
    if path.lower().endswith('.jsonl'):
        return _read_jsonl(path)
    return _read_csv(path)


def _read_csv(path: str) -> List[Candidate]:
    with open(path, 'r', encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        names = set(reader.fieldnames or [])
        if not names & {'Name', 'name', 'original_name'}:
            raise ValueError('CSV requires a Name, name or original_name column')
        records = [Candidate.from_dict(row) for row in reader]
    return [r for r in records if r]


def _read_jsonl(path: str) -> List[Candidate]:
    records = []
    with open(path, 'r', encoding='utf-8') as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except ValueError as exc:
                raise ValueError('Invalid JSONL on line {}: {}'.format(number, exc))
            record = Candidate.from_dict(data)
            if record:
                records.append(record)
    return records

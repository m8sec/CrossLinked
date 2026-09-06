# Outputs, run states and exit codes

Every invocation writes a set of files under the `-o` prefix (default `names`).
Nothing in them is verified: names, titles, affiliations and generated
addresses are candidates drawn from search-result titles.

| File | Mode | Written | Contents |
|---|---|---|---|
| `<prefix>.csv` | search | appended | Raw evidence, one row per unique profile as it arrives: `Datetime,Search,Name,Title,URL,rawText`. Survives interrupted runs. |
| `<prefix>.review.csv` | both, when an organization is known | overwritten | Every candidate with its classification, reason and name issue. |
| `<prefix>.jsonl` | both | overwritten | One JSON object per candidate. Reviewed records when classification ran, plain candidates otherwise. |
| `<prefix>.txt` | both | overwritten | Formatted account names selected for export. Empty when nothing qualified. |
| `<prefix>.run.json` | both | overwritten | Run summary: mode, status, exit code, per-provider state, counts and output paths. |

Search mode classifies against the company name automatically. Parse mode
classifies only when `--organization` is given; without it the JSONL contains
plain candidates and the TXT is a pure reformat.

Timestamps in new records are ISO 8601 with the local offset. Older raw CSV rows
keep the previous `MM-DD-YYYY HH:MM:SS` form; the column is informational only.

## Re-processing an export

Any of the raw CSV, the review CSV, or the JSONL file can be passed back as the
positional argument instead of a company name:

```bash
python crosslinked.py names.jsonl --organization 'Example University' -f '{f}{last}' -o second_pass
```

The reader accepts both header styles (`Name`/`URL`/`rawText` and
`name`/`url`/`text`) and prefers `original_name` over the normalized `name` so a
second pass starts from the raw spelling. The output prefix must not point at
the input file.

## JSONL record fields

Plain candidates carry `name`, `title`, `url`, `text`, `snippet`, `engines`,
`observed_at` and `provider`. Reviewed records add `original_name`,
`classification`, `reason`, `name_issue` and `evidence_status`, with `name`
holding the normalized form. Classification values are documented in the
[result quality guide](result-quality.md).

## Provider states

Each provider ends in exactly one status with a stop reason:

| Status | Meaning | Exit code |
|---|---|---|
| `complete` | Pagination finished naturally (empty page). | 0 |
| `limited` | Stopped by a budget: page limit, time budget, repeated page, or a keyboard interrupt. | 0 |
| `partial` | Results were returned but at least one upstream engine failed; coverage is incomplete. | 1 |
| `failed` | The provider stopped on an error: HTTP failure, invalid response, or validation failure. | 1 |

Stop reasons currently emitted: `page_limit`, `time_budget`, `empty_page`,
`empty_page_with_engine_failures`, `repeated_page`, `request_failure`,
`validation_failed`, `http_<code>` (Google/Bing non-200 responses) and
`interrupted`.

Google and Bing now report `failed` on the first non-200 response instead of
silently ending. That is the usual signal for blocking or a CAPTCHA, so a
default `google,bing` run that gets blocked exits 1 like a failed SearXNG run.

## Run summary

`<prefix>.run.json` aggregates the providers. Its `status` is the worst
provider status (`complete` for parse mode, which has no providers) and
`exit_code` is 1 for `partial` or `failed`. It also records `candidates`
(records collected or read), `selected` (names written to TXT), the
classification counts, the organization used, the source file in parse mode,
and every output path. `schema_version` is 1.

A keyboard interrupt marks the run `interrupted`, keeps whatever was written,
and exits 0.

## Programmatic use

The same objects are importable:

- `crosslinked.models.Candidate`, `ReviewedCandidate`, `ProviderState`, `RunState`
- `crosslinked.provider.Provider` is the interface every backend implements
  (`validate()`, `search()`, `run()`, `add_result()`); providers stream new
  candidates to any callables in `provider.sinks`.
- `crosslinked.build_provider(name, args)` constructs a provider from parsed CLI
  arguments; `crosslinked.execute(args)` runs everything and returns the `RunState`.
- `crosslinked.output` holds the readers and writers for every file above.
- `crosslinked.quality.review(records, organization, aliases, excluded)` returns
  `ReviewedCandidate` objects.

## Validation

```bash
python -m unittest discover -s tests -v
python -m mypy
```

The GitHub Actions workflow in `.github/workflows/tests.yml` runs the suite on
several Python versions with outbound HTTP pointed at a closed local port, so a
test that reaches the network fails instead of depending on a search engine.

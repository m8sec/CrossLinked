# Result quality and affiliation review

Live searches now write `<prefix>.review.csv` with **every candidate**, alongside
the existing raw CSV. TXT defaults to current staff/student candidates that have
a usable normalized name. No class means verified employment or enrollment.

## Review an existing run without searching again

In Kali, activate your environment and change to your checkout, then run:

```bash
python crosslinked.py names.csv \
  --organization 'Newcastle University' \
  -f '{first}.{last}' -o newcastle_review
```

This preserves `names.csv`, writes `newcastle_review.review.csv`,
`newcastle_review.jsonl` and `newcastle_review.run.json`, and writes the
selected names to `newcastle_review.txt`. Parse mode no longer creates an empty
raw CSV. Keep different output prefixes for separate reviews. A JSONL or review
CSV export can be passed back in the same way; see the [outputs guide](outputs.md).

Without `--organization`, CSV mode remains a name-reformatting operation; it does
not classify affiliations. Names are normalized in either mode.

## Categories

| Classification | Meaning | Default TXT |
|---|---|---|
| current_staff_candidate | Explicit role associated with the target in the title | Included if name is usable |
| current_student_candidate | Explicit student/study relationship with the target | Included if name is usable |
| former_affiliation | Explicit former, retired, graduate or alumni wording | Excluded |
| organization_mismatch | Conflicting organization, without an accepted target mention | Excluded |
| non_person | Name resembles a group or organization | Excluded |
| uncertain | Missing, truncated, conflicting or insufficient affiliation evidence | Review only |

Graduate students remain student candidates; graduates/alumni do not. Emeritus,
prospective/incoming affiliations and student society leadership remain uncertain.
A society role alone does not prove enrollment or employment.

Matching uses exact phrases with word boundaries and case-insensitive comparison.
`Newcastle University` and `University of Newcastle` are not treated as aliases.
To accept a known alternative name, repeat `--org-alias 'Alternative Name'`.
To flag an unrelated institution, repeat `--exclude-org 'Other Institution'`.
These options classify evidence; they do not change the provider's search query.

Use `--include-uncertain` to include uncertain affiliations in TXT. This does not
include former affiliations, organization mismatches, group accounts, or unresolved
names. All remain visible in the review CSV regardless of this option.

## Name cleanup and evidence

Common honorifics and known credential suffixes are removed for name generation.
Hyphenated names, apostrophes and surname particles are retained. Initials are
not expanded. Incomplete names and unresolved punctuation/credentials are flagged
in `name_issue` and excluded from classified TXT exports.

The review retains original and normalized names, classification, reason, name
issues, profile URL, title, provider, and observation time when supplied. New SearXNG runs
also retain snippets and upstream engine attribution. Existing CSV files cannot
recover snippets or engine attribution that were never saved.

The classifier deliberately uses title evidence, not snippets that may combine
education and employment from different dates. It is rule-based and primarily
supports English titles. It can miss legitimate people; unfamiliar group names
can remain uncertain. Search titles may be stale, and collection time is not
the date the affiliation was last verified. Review the original evidence before
treating any affiliation as current. Formatting assumes first/last name ordering;
it cannot determine a person's preferred name or an organization's account policy.

## Validation

```bash
python -m unittest discover -s tests -v
```

Synthetic tests cover current students (including graduate students), alumni,
staff, emeritus and prospective roles, organization ambiguity, group accounts,
credential cleanup, incomplete names, and offline export preservation. Real
search outputs are kept local and are not committed as test fixtures.

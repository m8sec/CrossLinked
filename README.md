<div align="center">
    <h1>CrossLinked</h1>
</div>

<p align="center">
    <a href="https://github.com/a7t0fwa7/CrossLinked"><img src="https://img.shields.io/badge/GitHub-@a7t0fwa7-blue?style=plastic&logo=github"/></a>&nbsp;&nbsp;
    <a href="https://github.com/a7t0fwa7/CrossLinked/actions/workflows/tests.yml"><img src="https://github.com/a7t0fwa7/CrossLinked/actions/workflows/tests.yml/badge.svg?branch=codex%2Fresult-quality"/></a>&nbsp;&nbsp;
    <a href="/LICENSE"><img src="https://img.shields.io/badge/License-GPL%20v3.0-green.svg?style=plastic"/></a>&nbsp;&nbsp;
</p>

CrossLinked is a LinkedIn enumeration tool that uses search engine scraping to collect employee names from an
organization. It works without API keys, credentials, or accessing LinkedIn directly.

This repository is the **V2 fork maintained by [@a7t0fwa7](https://github.com/a7t0fwa7)**. CrossLinked was
originally written by [@m8sec](https://github.com/m8sec/CrossLinked); the original code and this fork are both
licensed under GPLv3.

## What the fork adds

- **SearXNG provider** (`--search searxng`): JSON results from an instance you control, bounded pagination,
  engine selection and validation, retries, page caching with `--resume`, and explicit stop reasons.
  See the [SearXNG setup and usage guide](docs/searxng.md).
- **Affiliation review**: every candidate is classified as a current staff/student candidate, former
  affiliation, organization mismatch, group account or uncertain, with the reason kept in a review CSV.
  See the [result quality guide](docs/result-quality.md).
- **Structured outputs and run states**: a JSONL export, a `<prefix>.run.json` summary with per-provider
  status and exit code, and typed `Candidate`/`Provider`/`RunState` classes. Exports can be fed back in as
  input. See the [outputs guide](docs/outputs.md).
- **Offline tests and type checks** in GitHub Actions (`.github/workflows/tests.yml`).

The upstream Google and Bing scrapers are still available and remain the default, but their current scraping
behaviour has not been verified in this fork. Blocked responses are now reported as a failed provider.

All names, titles, affiliations and generated addresses are **unverified candidates**. Only use this tool
against organizations you are authorized to assess.

## Table of Contents
- [Install](#install)
- [Prerequisites](#prerequisites)
    + [Naming Format](#naming-format)
    + [Advanced Formatting](#advanced-formatting)
- [Search](#search)
  * [Example Usage](#example-usage)
  * [Screenshots](#screenshots)
- [Parse](#parse)
  * [Example Usage](#example-usage-1)
- [Additional Options](#additional-options)
  * [Proxy Rotation](#proxy-rotation)
- [Command-Line Arguments](#command-line-arguments)
- [Development](#development)
- [Contribute](#contribute)
- [Credits](#credits)

# Install
The PyPI package `crosslinked` is the upstream release and does not contain the fork's changes. Install this
fork from GitHub. The development branch is `codex/result-quality` until it is merged into `master`.

### Python
```bash
git clone --branch codex/result-quality https://github.com/a7t0fwa7/CrossLinked.git
cd CrossLinked
pip3 install .
```

### Poetry
Install and run the latest code using [Poetry](https://python-poetry.org/docs/#installing-with-the-official-installer):
```bash
git clone --branch codex/result-quality https://github.com/a7t0fwa7/CrossLinked.git
cd CrossLinked
poetry install
poetry run crosslinked -h
```

### Run from the checkout
```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/python crosslinked.py -h
```

A Kali WSL walkthrough, including a local SearXNG container, is in the [SearXNG guide](docs/searxng.md).

# Prerequisites
CrossLinked assumes the organization's account naming convention has already been identified. This is required for execution and should be added to the CMD args based on your expected output. See the [Naming Format](#naming-format) and [Example Usage](#example-usage) sections below:

### Naming Format
```text
{first}.{last}          = john.smith
CMP\{first}{l}          = CMP\johns
{f}{last}@company.com   = jsmith@company.com
```

> 🦖 ***Still stuck?** Metadata is a good place to check for hidden information such as the account naming convention. See [PyMeta](https://github.com/m8sec/pymeta) for more.*
<br>


### Advanced Formatting
To be compatible with alternate naming conventions CrossLinked allows users to control the index position of the name extracted from search text. Should the name not be long enough, or errors be encountered with the search string, CrossLinked will revert back to its default format.

***Note**: the search string array starts at `0`. Negative numbers can also be used to count backwards from the last value.*

```
# Default output
python3 crosslinked.py -f '{first}.{last}@company.com' Company
John David Smith = john.smith@company.com

# Use the second-to-last name as "last"
python3 crosslinked.py -f '{0:first}.{-2:last}@company.com' Company
John David Smith    = john.david@company.com
Jane Doe            = jane.doe@company.com

# Use the second item in the array as "last"
python3 crosslinked.py -f '{first}.{1:last}@company.com' Company
John David Smith    = john.david@company.com
Jane Doe            = jane.doe@company.com
```


# Search
By default, CrossLinked uses the `google` and `bing` search engines to identify employees of the target
organization. Add `--search searxng --searxng-url http://localhost:8080` to use a SearXNG instance instead.
After execution, these files appear in the current directory unless `-o` changes the prefix:

* *names.txt* - Unique user accounts in the specified format, limited to current staff/student candidates with usable names.
* *names.csv* - Raw search evidence, appended across runs. See the `Parse` section below.
* *names.review.csv* - Every candidate with its classification and reason.
* *names.jsonl* - The same records as JSON lines, one per candidate.
* *names.run.json* - Run summary: provider status, stop reason, counts and exit code.

The process exits 1 when any provider failed or lost upstream coverage, so partial results are never mistaken
for complete ones. See the [outputs guide](docs/outputs.md).


## Example Usage
```bash
python3 crosslinked.py -f '{first}.{last}@domain.com' company_name
```

```bash
python3 crosslinked.py -f 'domain\{f}{last}' -t 15 -j 2 company_name
```

```bash
python3 crosslinked.py --search searxng --searxng-url http://localhost:8080 -t 60 --max-pages 5 -j 5 -f '{first}.{last}' 'Target Company'
```
> ⚠️ For best results, use the company name as it appears on LinkedIn `"Target Company"` not the domain name.


## Screenshots
Upstream screenshot of a Google/Bing run; the fork prints additional provider status lines.

![](https://user-images.githubusercontent.com/13889819/190488899-0f4bea2d-6c31-422f-adce-b56f7be3d906.png)


# Parse
*Account naming convention changed after execution and now you're hitting CAPTCHA requests? No problem.*

The raw `names.csv`, the review CSV and the JSONL export all store the collected evidence (`name`, `job title`
and `url`). Any of them can be passed back in place of a company name to reformat accounts without searching
again. Add `--organization` to re-run the affiliation review; without it the file is only reformatted.


## Example Usage
```bash
python3 crosslinked.py -f '{f}{last}@domain.com' names.csv
```

```bash
python3 crosslinked.py names.jsonl --organization 'Target Company' -f '{f}{last}@domain.com' -o second_pass
```


# Additional Options
## Proxy Rotation
CrossLinked provides proxy support to rotate source addresses. Users can input a single proxy with `--proxy 127.0.0.1:8080` or use multiple via `--proxy-file proxies.txt`.


```bash
> cat proxies.txt
127.0.0.1:8080
socks4://111.111.111.111
socks5://222.222.222.222

> python3 crosslinked.py --proxy-file proxies.txt -f '{first}.{last}@company.com' -t 10 "Company"
```
> ⚠️ `HTTP/S` proxies can be added by IP:Port notation. However, socks proxies will require a `socks4://` or `socks5://` prefix.


# Command-Line Arguments
```
positional arguments:
  company_name          Target company name, or an existing .csv/.jsonl export to re-process

options:
  -h, --help            show this help message and exit
  -t TIMEOUT            Max timeout per search (Default=15)
  -j JITTER             Jitter between requests (Default=1)

Search arguments:
  --search ENGINE       Search Engine (Default='google,bing')
  --searxng-url SEARXNG_URL
                        SearXNG instance URL (or SEARXNG_URL environment variable)
  --max-pages MAX_PAGES
                        Maximum SearXNG pages (Default=5)
  --request-timeout REQUEST_TIMEOUT
                        SearXNG request timeout, capped by remaining search budget (Default=30)
  --retries RETRIES     Retries for transient SearXNG connection/502/503/504 failures (0-3, Default=2)
  --searxng-engines SEARXNG_ENGINES
                        Comma-separated SearXNG engine names, e.g. google,bing
  --cache-dir CACHE_DIR
                        Save SearXNG response pages in this directory
  --resume              Reuse saved complete pages; retry partial pages (requires --cache-dir)

Output arguments:
  -f NFORMAT            Format names, ex: 'domain\{f}{last}', '{first}.{last}@domain.com'
  -o OUTFILE            Change name of output file (omit_extension)
  --organization ORGANIZATION
                        Organization to classify against when reading an existing CSV/JSONL
  --org-alias ORG_ALIAS
                        Additional exact organization name accepted (repeatable)
  --exclude-org EXCLUDE_ORG
                        Conflicting organization name to flag (repeatable)
  --include-uncertain   Include uncertain affiliations in TXT; review CSV always retains all records

Proxy arguments:
  --proxy PROXY         Proxy requests (IP:Port)
  --proxy-file PROXY    Load proxies from file for rotation
```


# Development
```bash
python -m unittest discover -s tests -v
python -m mypy
```

The test suite is fully offline: providers are exercised with mocks and a loopback HTTP fixture. The same
checks run in GitHub Actions on every push and pull request.


# Contribute
Contribute to the project by:
* Like and share the tool!
* Open an [issue](https://github.com/a7t0fwa7/CrossLinked/issues) to report a problem or, better yet, initiate a PR.
* Reach out with potential features or improvements via [@a7t0fwa7](https://github.com/a7t0fwa7).


# Credits
* [@m8sec](https://github.com/m8sec) wrote the original CrossLinked and the Google/Bing scrapers.
* [@a7t0fwa7](https://github.com/a7t0fwa7) maintains this V2 fork.
* Contributors to the upstream project are listed in its [commit history](https://github.com/m8sec/CrossLinked/commits).

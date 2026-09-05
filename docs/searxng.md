# SearXNG provider

Use a SearXNG instance you operate or are permitted to query. No public instance
is selected automatically. SearXNG depends on upstream search providers; this
integration does not contact LinkedIn directly.

Merge this into the instance's `settings.yml`, preserving other settings, then restart:

```yaml
search:
  formats:
    - html
    - json
```

Configure upstream engines in SearXNG itself. Official documentation:
[installation](https://docs.searxng.org/admin/installation.html),
[JSON search API](https://docs.searxng.org/dev/search_api.html).

## Kali WSL: setup on a new Windows device

These steps use Docker Desktop's Linux engine, with CrossLinked running inside
Kali WSL. Docker Desktop hosts SearXNG; activating the Python environment does
not start Docker.

1. Install Docker Desktop and Kali under WSL 2.
2. Open Docker Desktop and enable its WSL 2 engine. Under **Settings → Resources
   → WSL Integration**, enable Kali, then apply the changes.
3. Enable **Start Docker Desktop when you sign in** in Docker Desktop settings
   if you want the service available after Windows login.
4. Open Kali and check `sudo docker info`. If it cannot connect, start Docker
   Desktop and check Kali integration before continuing.

See [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/)
and [Docker WSL integration](https://docs.docker.com/desktop/features/wsl/).

### Create SearXNG once

Run these commands in Kali. The configuration command is for a **new device**;
do not overwrite an existing `settings.yml` containing your custom settings.

```bash
mkdir -p ~/searxng/config
cd ~/searxng

cat > config/settings.yml <<EOF
use_default_settings: true
server:
  secret_key: "$(openssl rand -hex 32)"
  limiter: false
search:
  formats:
    - html
    - json
EOF

sudo docker run -d \
  --name crosslinked-searxng \
  --restart unless-stopped \
  -p 127.0.0.1:8080:8080 \
  -v "$HOME/searxng/config:/etc/searxng" \
  -v crosslinked-searxng-data:/var/cache/searxng \
  searxng/searxng:latest
```

The published port is local to your computer. Open `http://localhost:8080` or
test JSON from Kali:

```bash
curl -fsS 'http://localhost:8080/search?q=searxng&format=json'
```

If Docker reports the container name already exists, inspect it with
`sudo docker ps -a --filter name=crosslinked-searxng` and start the existing
container instead of repeating `docker run`.

### Set up CrossLinked in Kali

On the original device, the modified checkout is at:

```bash
cd /mnt/d/Github_Projects/Crosslinked-V2.0
```

On a new device, clone the development branch containing SearXNG support:

```bash
mkdir -p ~/projects
cd ~/projects
git clone --branch codex/result-quality https://github.com/a7t0fwa7/CrossLinked.git
cd CrossLinked
```

Use this checkout's path for subsequent commands on the new device. The fork's
default branch may not contain these changes until they are merged. After
installing dependencies below, verify that `python crosslinked.py --help` lists
`--searxng-url`.

Create a fresh Linux environment; do not reuse a Windows virtual environment:

```bash
sudo apt update
sudo apt install -y python3-venv curl openssl
python3 -m venv ~/.venvs/crosslinked
source ~/.venvs/crosslinked/bin/activate
pip install requests beautifulsoup4 lxml Unidecode
```

From the checkout directory, run a search (names only):

```bash
python crosslinked.py 'Newcastle University' \
  --search searxng \
  --searxng-url http://localhost:8080 \
  -t 60 --max-pages 5 -j 5 \
  -f '{first}.{last}' \
  -o newcastle_search
```

For email-shaped output, supply your intended pattern and domain explicitly.
`example.com` in other examples is a placeholder, not a discovered domain.
Outputs are written in the current directory: TXT is overwritten and CSV is
appended. Use a different `-o` prefix to preserve separate runs.

## Everyday startup and shutdown

**You do not need to reinstall SearXNG or repeat `docker run` each time.**
The `unless-stopped` policy starts the container when Docker starts, unless you
previously stopped the container manually. Docker must itself be running;
opening Kali or activating Python alone does not guarantee that.

After Windows login, let Docker Desktop finish starting. In Kali:

```bash
# Check running containers
sudo docker ps --filter name=crosslinked-searxng

# Start it if you previously stopped it
sudo docker start crosslinked-searxng

# Activate CrossLinked for this shell
source ~/.venvs/crosslinked/bin/activate
cd /mnt/d/Github_Projects/Crosslinked-V2.0
```

Useful management commands:

```bash
# Show running and stopped containers
sudo docker ps -a --filter name=crosslinked-searxng

# Confirm the restart policy
sudo docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' crosslinked-searxng

# Set the policy if an existing container was created without it
sudo docker update --restart unless-stopped crosslinked-searxng

# Restart after editing ~/searxng/config/settings.yml
sudo docker restart crosslinked-searxng

# Stop deliberately (it stays stopped until you start it again)
sudo docker stop crosslinked-searxng

# Diagnose startup or search problems
sudo docker logs --tail 50 crosslinked-searxng
```

If you used the earlier Windows setup, the configuration may instead be in
`D:\Docker\SearXNG\config`. Inspect the existing container's mounts before
editing a different copy of the configuration:

```bash
sudo docker inspect -f '{{json .Mounts}}' crosslinked-searxng
```

### Understand partial searches

An upstream engine can return access denied (403), rate limiting (429), or a
CAPTCHA while other engines still return results. SearXNG then temporarily
suspends the affected engine. Those failures do not erase collected records.
Restarting the container does not resolve the provider's underlying rejection.
Allow cooldowns to expire; a longer `-j` delay can reduce request frequency but
does not guarantee provider acceptance.

```bash
sudo docker logs --since 30m crosslinked-searxng 2>&1 \
  | grep -iE 'duckduckgo|403|429|captcha|denied'
```

## Run from this repository (PowerShell alternative)

```powershell
python -m venv venv
./venv/Scripts/python -m pip install requests beautifulsoup4 lxml Unidecode
./venv/Scripts/python crosslinked.py 'Example Company' --search searxng --searxng-url http://localhost:8080 -t 60 --max-pages 5 -f '{first}.{last}@example.com'
```

Alternatively set `$env:SEARXNG_URL = 'http://localhost:8080'`. URLs can include a
deployment subpath or end in `/search`; credentials, queries and fragments are
rejected. HTTPS verifies certificates. Existing proxy flags are supported.

Live searches produce `names.txt`, raw `names.csv`, `names.review.csv`,
`names.jsonl` and `names.run.json` (see the [outputs guide](outputs.md)).
TXT selects staff/student candidates with usable names; the review CSV preserves
all candidates and reasons. See [result quality](result-quality.md) for offline
classification, organization aliases and uncertain results. Raw CSV records the search-result title
and normalized profile URL. Names and job titles are inferred from titles;
employment and generated email addresses are not verified. The first record for
a profile wins. Regional LinkedIn URLs and tracking parameters are deduplicated.

## Status

### Engine selection and saved progress

Use `--searxng-engines 'google cse,brave'` to request particular engine names
from your instance. Names must match SearXNG; provider availability and access
are still controlled by the instance. Omitting this flag uses instance defaults.
Test one engine at a time with `--max-pages 1` before combining providers.

Explicit engine requests omit `categories`: SearXNG adds category engines to an
explicit engine list when both parameters are present. An earlier implementation
sent both and unintentionally included the default general engines. Cache keys
were versioned after this fix, so those older response pages are not reused.

```bash
python crosslinked.py 'Newcastle University' \
  --search searxng --searxng-url http://localhost:8080 \
  --searxng-engines 'google cse' \
  --cache-dir .crosslinked-cache -t 60 -j 5 --max-pages 1 \
  -f '{first}.{last}' -o newcastle_engine_test
```

Add `--resume` to reuse saved complete pages and retry partial pages. Increase
`--max-pages` to continue beyond the previous page budget. Cache keys include
instance, target, engine selection and page. Earlier partial-page records are
preserved when a retry returns fewer records. Cached evidence retains its original
observation time; it is not a fresh affiliation check. Use a new cache directory
for an independent fresh dataset. Avoid concurrent runs sharing a cache directory.
Raw CSV is appended on reruns, so use a new output prefix when resuming if you
want a separate raw export. Review/TXT exports are rebuilt for the current run.

Each engine failure is printed once per run, with affected engines summarized at
the end. SearXNG remains responsible for upstream cooldowns; CrossLinked does not
reset them or automatically retry access-denied/CAPTCHA responses. Empty failed
pages are reported as `empty_page_with_engine_failures`, distinct from a clean
`empty_page`. Other stop reasons are `page_limit`, `time_budget`, `repeated_page`
and `request_failure`.

Explicit engine selection is validated against the instance's `/config` before
searching. Unknown names, an unavailable configuration endpoint, or a malformed
engine list stop that provider instead of risking fallback to default engines.
Disabled-by-default but installed engines are accepted. The configuration check
has its own bounded timeout before the search time budget begins.

The CLI defaults to `--retries 2` (allowed range 0–3). Connection failures,
timeouts, and HTTP 502/503/504 from the SearXNG endpoint get exponential delays
of 2, 4, then 8 seconds, bounded by the remaining search budget. Numeric
`Retry-After` headers are respected; an unparseable/date header or a delay longer
than the remaining budget stops retries. HTTP 403/429, invalid JSON, and
upstream errors embedded in JSON are not automatically retried. Use
`--retries 0` for no automatic retries. Upstream cooldowns remain SearXNG's job.

### Local provider smoke test, 5 September 2026

One page per engine for the same Newcastle University profile query, with five
seconds between engines. This is a single-run snapshot, not a coverage benchmark.

| Engine | Unique profiles | Staff/student candidates | Outcome |
|---|---:|---:|---|
| google cse | 20 | 4 | No reported upstream error; request took 22.9 seconds |
| yandex | 6 | 0 | No reported upstream error; affiliation evidence insufficient for default selection |
| brave | 0 | 0 | Too many requests |
| baidu | 0 | 0 | CAPTCHA |
| mojeek | 0 | 0 | Access denied |
| qwant | 0 | 0 | CAPTCHA |

Counts are unique within each engine, not incremental across engines. Explicit
engine selection queried Yandex even though `/config` marked it disabled by
default; the default-enabled flag is not a reliable test of whether explicit
selection can use an installed adapter. No instance defaults were changed.
The slow Google CSE response motivated raising the client request timeout to 30
seconds. Use `-t 120 --request-timeout 30` when allowing several pages; both limits
remain subject to the socket-timeout caveat below.

- `complete`: reached an empty page; does not establish exhaustive coverage.
- `limited`: page/time budget reached or a repeated page detected.
- `partial`: SearXNG reported upstream engine failures.
- `failed`: HTTP/network error, invalid JSON or an unexpected response schema.

Partial/failed searches retain collected records and exit with code 1. HTTP 403
includes JSON configuration guidance. Requests use the remaining search budget,
capped at 30 seconds per request (configurable with `--request-timeout`). These are socket inactivity timeouts, not a
strict wall-clock deadline. Blocked requests are not retried automatically.

## Verification

```powershell
./venv/Scripts/python -m unittest discover -s tests -v
```

Tests simulate responses. Live coverage must be benchmarked with a configured
instance. This addition does not repair legacy Google/Bing scraping or implement
browser automation, YaCy, or the planned Pi extension.

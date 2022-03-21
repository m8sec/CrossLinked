# CrossLinked
<p align="center">
    <img src="https://img.shields.io/badge/License-GPL%20v3.0-green?style=plastic"/>&nbsp;
    <a href="https://www.twitter.com/m8r0wn">
        <img src="https://img.shields.io/badge/Twitter-@m8r0wn-blue?style=plastic&logo=twitter"/>
    </a>&nbsp;
    <a href="https://github.com/sponsors/m8r0wn">
        <img src="https://img.shields.io/badge/Sponsor-GitHub-red?style=plastic&logo=github"/>
    </a>&nbsp;
 </p>

CrossLinked is a LinkedIn enumeration tool that uses search engine scraping to collect valid employee names from a target 
organization. This technique provides accurate results without the use of API keys, credentials, or even accessing 
the site directly. Formats can then be applied in the command line arguments to turn these names into email addresses, 
domain accounts, and more.

## Setup
```bash
git clone https://github.com/m8r0wn/crosslinked
cd crosslinked
pip3 install -r requirements.txt
```

## Examples
*Results are written to a 'names.txt' file in the current directory unless specified in the command line arguments.
See the <a href="#Usage">Usage</a> section for additional options.*
```bash
python3 crosslinked.py -f '{first}.{last}@domain.com' company_name
```

```bash
python3 crosslinked.py -f 'domain\{f}{last}' -t 45 -j 1 company_name
```

## Usage
```
positional arguments:
  company_name        Target company name

optional arguments:
  -h, --help          show this help message and exit
  -t TIMEOUT          Max timeout per search (Default=20, 0=None)
  -j JITTER           Jitter between requests (Default=0)
  -v                  Show names and titles recovered after enumeration

Search arguments:
  -H HEADER           Add Header ('name1=value1;name2=value2;')
  --search ENGINE     Search Engine (Default='google,bing')
  --safe              Only parse names with company in title (Reduces false positives)

Output arguments:
  -f NFORMAT          Format names, ex: 'domain\{f}{last}', '{first}.{last}@domain.com'
  -o OUTFILE          Change name of output file (default=names.txt

Proxy arguments:
  --proxy PROXY       Proxy requests (IP:Port)
  --proxy-file PROXY  Load proxies from file for rotation
```

## Proxy Support
The latest version of CrossLinked provides proxy support through the <a href='https://github.com/m8r0wn/taser'>Taser</a>
library. Users can mask their traffic with a single proxy by adding ```--proxy 127.0.0.1:8080``` to the command line 
arguments, or use ```--proxy-file proxies.txt``` for rotating source addresses.

```http/https``` proxies can be added in ```IP:PORT``` notation, while SOCKS requires a ```socks4://``` or 
```socks5://``` prefix.



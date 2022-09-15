# CrossLinked
<p align="center">
    <img src="https://img.shields.io/badge/License-GPL%20v3.0-green?style=plastic"/>&nbsp;
    <a href="https://www.twitter.com/m8sec">
        <img src="https://img.shields.io/badge/Twitter-@m8sec-blue?style=plastic&logo=twitter"/>
    </a>&nbsp;
    <a href="https://github.com/sponsors/m8sec">
        <img src="https://img.shields.io/badge/Sponsor-GitHub-red?style=plastic&logo=github"/>
    </a>&nbsp;
 </p>

CrossLinked is a LinkedIn enumeration tool that uses search engine scraping to collect valid employee names from an 
organization. This technique provides accurate results without the use of API keys, credentials, or accessing 
LinkedIn directly!


## Install
Install the last stable release from PyPi:
```commandline
pip3 install crosslinked
```
Or, install the most recent code from GitHub:
```bash
git clone https://github.com/m8sec/crosslinked
cd crosslinked
python3 setup install
```


## Prerequisite
CrossLinked assumes the organization's account naming convention has already been identified. This is required for execution and should be added to the CMD args based on your expected output. See the `Naming Format` and `Example Usage` sections below:

### Naming Format
```text
{f}.{last}              = j.smith
{first.{last}           = john.smith
CMP\{first}{l}          = CMP\johns
{f}{last}@company.com   = jsmith@company.com
```

> ***Still Stuck?** Metadata is always a good place to check for hidden information such as account naming convention. see [PyMeta](https://github.com/m8sec/pymeta) for more.*


## Search
By default, CrossLinked will use `google` and `bing` search engines to identify employees of the target organization. After execution, two files (`names.txt` & `names.csv`) will appear in the current directory, unless modified in the CMD args.

* *names.txt* - List of unique user accounts in the specified format.
* *names.csv* - Raw search data. See the `Parse` section below for more.


### Example Usage
```bash
python3 crosslinked.py -f '{first}.{last}@domain.com' company_name
```

```bash
python3 crosslinked.py -f 'domain\{f}{last}' -t 15 -j 2 company_name
```

> ***Note:** For best results, use the company name as it appears on LinkedIn `"Target Company"` not the domain name.*


### Screenshots
![](https://user-images.githubusercontent.com/13889819/190488899-0f4bea2d-6c31-422f-adce-b56f7be3d906.png)


## Parse
:boom: **New Feature** :boom:

*Account naming convention changed after execution and now your hitting CAPTCHA requests? No Problem!*

CrossLinked v0.2.0 now includes a `names.csv` output file, which stores all scraping data including: `first name`, `last name`, `job title`, and `url`. This can be ingested and parsed to reformat user accounts as needed.

### Example Usage
```
python3 crosslinked.py -f '{f}{last}@domain.com' names.csv
```

### Screenshots
![](https://user-images.githubusercontent.com/13889819/190494309-c6da8cdc-4312-4e53-a0bb-1fffbc9698e4.png)


## Additional Options
### Proxy Rotation
The latest version of CrossLinked provides proxy support to rotate source addresses. Users can input a single proxy with `--proxy 127.0.0.1:8080` or use multiple via `--proxy-file proxies.txt`.


```bash
> cat proxies.txt
127.0.0.1:8080
socks4://111.111.111.111
socks5://222.222.222.222

> python3 crosslinked.py --proxy-file proxies.txt -f '{first}.{last}@company.com' -t 10 "Company"
```

> ***Note:** `HTTP/S` proxies can be added by IP:Port notation. However, socks proxies will require a `socks4://` or `socks5://` prefix.*


### Usage
```
positional arguments:
  company_name        Target company name

optional arguments:
  -h, --help          show help message and exit
  -t TIMEOUT          Max timeout per search (Default=20, 0=None)
  -j JITTER           Jitter between requests (Default=0)

Search arguments:
  --search ENGINE     Search Engine (Default='google,bing')

Output arguments:
  -f NFORMAT          Format names, ex: 'domain\{f}{last}', '{first}.{last}@domain.com'
  -o OUTFILE          Change name of output file (omit_extension)

Proxy arguments:
  --proxy PROXY       Proxy requests (IP:Port)
  --proxy-file PROXY  Load proxies from file for rotation
```


## Contribute
Contribute to the project by:
* Like and share the tool!
* Create an issue to report any problems or, better yet, initiate a PR.
* Reach out with any potential features or improvements [@m8sec](https://twitter.com/m8sec).

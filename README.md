<div align="center">
    <h1>CrossLinked</h1>
</div>

<p align="center">
    <img src="https://img.shields.io/badge/Version-v0.3.0-green"/>&nbsp;
    <a href="https://www.twitter.com/m8sec">
        <img src="https://img.shields.io/badge/Twitter-@m8sec-gray?logo=twitter"/>
    </a>&nbsp;
    <img src="https://img.shields.io/badge/python-3.6%20|%203.7%20|%203.8%20|%203.9%20|%203.10%20-blue.svg"/>&nbsp;
</p>


CrossLinked is a LinkedIn enumeration tool that uses search engine scraping to collect valid employee names from an 
organization. This technique provides accurate results without the use of API keys, credentials, or accessing 
LinkedIn directly!


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
  * [Screenshots](#screenshots-1)
- [Additional Options](#additional-options)
  * [Proxy Rotation](#proxy-rotation)
- [Command-Line Arguments](#command-line-arguments)
- [Contribute](#contribute)


# Sponsors
> 🚩 Consider sponsoring this project to ensure the latest improvements, have your company logo listed here, and get priority support - visit [github.com/sponsors/m8sec](https://github.com/sponsors/m8sec)


# Install
Install the last stable release from PyPi:
```commandline
pip3 install crosslinked
```
Or, install the most recent code from GitHub:
```bash
git clone https://github.com/m8sec/crosslinked
cd crosslinked
python3 setup.py install
```


# Prerequisites
CrossLinked assumes the organization's account naming convention has already been identified. This is required for execution and should be added to the CMD args based on your expected output. See the [Naming Format](#naming-format) and [Example Usage](#example-usage) sections below:

### Naming Format
```text
{first.{last}           = john.smith
CMP\{first}{l}          = CMP\johns
{f}{last}@company.com   = jsmith@company.com
```

> 🦖 ***Still Stuck?** Metadata is always a good place to check for hidden information such as account naming convention. see [PyMeta](https://github.com/m8sec/pymeta) for more.*
<br>


### Advanced Formatting
:boom: **New Feature** :boom:

To be compatible with alternate naming conventions CrossLinked allows users to control the index position of the name extracted from search text. Should the name not be long enough, or errors encountered with the search string, CrossLinked will revert back to its default format.

***Note**: the search string array starts at `0`. Negative numbers can also be used to count backwards from the last value.*

```
# Default output
crosslinked -f '{first}.{last}@company.com' Company
John David Smith = john.smith@company.com

# Use the second-to-last name as "last"
crosslinked -f '{0:first}.{-2:last}@company.com' Company
John David Smith    = john.david@company.com
Jane Doe            = jane.doe@company.com

# Use the second item in the array as "last"
crosslinked -f '{first}.{1:last}@company.com' Company
John David Smith    = john.david@company.com
Jane Doe            = jane.doe@company.com
```


# Search
By default, CrossLinked will use `google` and `bing` search engines to identify employees of the target organization. After execution, two files (`names.txt` & `names.csv`) will appear in the current directory, unless modified in the CMD args.

* *names.txt* - List of unique user accounts in the specified format.
* *names.csv* - Raw search data. See the `Parse` section below for more.


## Example Usage
```bash
python3 crosslinked.py -f '{first}.{last}@domain.com' company_name
```


```bash
python3 crosslinked.py -f 'domain\{f}{last}' -t 15 -j 2 company_name
```
> ⚠️ For best results, use the company name as it appears on LinkedIn `"Target Company"` not the domain name.


## Screenshots
![](https://user-images.githubusercontent.com/13889819/190488899-0f4bea2d-6c31-422f-adce-b56f7be3d906.png)


# Parse
*Account naming convention changed after execution and now your hitting CAPTCHA requests? No Problem!*

CrossLinked includes a `names.csv` output file, which stores all scraping data including: `name`, `job title`, and `url`. This can be ingested and parsed to reformat user accounts as needed.


## Example Usage
```
python3 crosslinked.py -f '{f}{last}@domain.com' names.csv
```

## Screenshots
![](https://user-images.githubusercontent.com/13889819/190494309-c6da8cdc-4312-4e53-a0bb-1fffbc9698e4.png)


# Additional Options
## Proxy Rotation
The latest version of CrossLinked provides proxy support to rotate source addresses. Users can input a single proxy with `--proxy 127.0.0.1:8080` or use multiple via `--proxy-file proxies.txt`.


```bash
> cat proxies.txt
127.0.0.1:8080
socks4://111.111.111.111
socks5://222.222.222.222

> python3 crosslinked.py --proxy-file proxies.txt -f '{first}.{last}@company.com' -t 10 "Company"
```
> ⚠️ `HTTP/S` proxies can be added by IP:Port notation. However, socks proxies will require a `socks4://` or `socks5://` prefix.*


# Command-Line Arguments
```
positional arguments:
  company_name        Target company name

optional arguments:
  -h, --help          show help message and exit
  -t TIMEOUT          Max timeout per search (Default=15)
  -j JITTER           Jitter between requests (Default=1)

Search arguments:
  --search ENGINE     Search Engine (Default='google,bing')

Output arguments:
  -f NFORMAT          Format names, ex: 'domain\{f}{last}', '{first}.{last}@domain.com'
  -o OUTFILE          Change name of output file (omit_extension)

Proxy arguments:
  --proxy PROXY       Proxy requests (IP:Port)
  --proxy-file PROXY  Load proxies from file for rotation
```


# Contribute
Contribute to the project by:
* Like and share the tool!
* Create an issue to report any problems or, better yet, initiate a PR.
* Reach out with any potential features or improvements [@m8sec](https://twitter.com/m8sec).

# CrossLinked

CrossLinked simplifies the processes of searching LinkedIn to collect valid employee names when performing password spraying or other security testing against an organization. Using similar search engine scraping capabilities found in tools like [subscraper](https://github.com/m8r0wn/subscraper) and [pymeta](https://github.com/m8r0wn/pymeta), CrossLinked will find valid employee names and help format the data according to the organization's account naming convention. Results will be written to a 'names.txt' file in the current directory for further testing.

## Setup
```bash
git clone https://github.com/m8r0wn/crosslinked
cd crosslinked
pip3 install -r requirements.txt
```

## Examples
```bash
python3 crosslinked.py -f '{first}.{last}@domain.com' company_name
```

```bash
python3 crosslinked.py -f 'domain\{f}{last}' -t 45 -j 0.5 company_name
```

## Usage
```
  -h, --help    show this help message and exit
  -t TIMEOUT    Timeout [seconds] for search threads (Default: 25)
  -j JITTER     Jitter for scraping evasion (Default: 0)
  -o OUTFILE    Change name of output file (default: names.txt
  -f NFORMAT    Format names, ex: 'domain\{f}{last}', '{first}.{last}@domain.com'
  -s, --safe    Only parse names with company in title (Reduces false positives)
  -v            Show names and titles recovered after enumeration
```

## Additions
Two additional scripts are included in this repo to aid in generating potential username and password files:

* ```pwd_gen.py``` - Generates custom password lists using words and variables defined at the top of the script. Perform number/letter substitutions, append special characters, and more. Once configured, run the script with no arguments to generate a 'passwords.txt'  output file.

* ```user_gen.py``` -  Generates custom usernames using inputs from firstname.txt and lastname.txt files, provided at the command line. Format is defined similiar to crosslinked.py and will be written to 'users.txt'. 

```bash
python3 user_gen.py -first top100_firstnames.txt -last top100_lastnames.txt -f "domain\{f}{last}"
```

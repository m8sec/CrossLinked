import logging
import requests
import threading
from time import sleep
from random import choice
from bs4 import BeautifulSoup
from unidecode import unidecode
from urllib.parse import urlparse
from crosslinked.logger import Log
from datetime import datetime, timedelta
from urllib3 import disable_warnings, exceptions

disable_warnings(exceptions.InsecureRequestWarning)
logging.getLogger("urllib3").setLevel(logging.WARNING)
csv = logging.getLogger('cLinked_csv')


class Timer(threading.Thread):
    def __init__(self, timeout):
        threading.Thread.__init__(self)
        self.start_time = None
        self.running = None
        self.timeout = timeout

    def run(self):
        self.running = True
        self.start_time = datetime.now()
        logging.debug("Thread Timer: Started")

        while self.running:
            if (datetime.now() - self.start_time) > timedelta(seconds=self.timeout):
                self.stop()
            sleep(0.05)

    def stop(self):
        logging.debug("Thread Timer: Stopped")
        self.running = False


class CrossLinked:
    def __init__(self, search_engine, target, timeout, conn_timeout=3, proxies=[], jitter=0):
        self.results = []
        self.url = {'google': 'https://www.google.com/search?q=site:linkedin.com/in+"{}"&num=100&start={}',
                    'bing': 'http://www.bing.com/search?q="{}"+site:linkedin.com/in&first={}'}

        self.runtime = datetime.now().strftime('%m-%d-%Y %H:%M:%S')
        self.search_engine = search_engine
        self.conn_timeout = conn_timeout
        self.timeout = timeout
        self.proxies = proxies
        self.target = target
        self.jitter = jitter

    def search(self):
        search_timer = Timer(self.timeout)
        search_timer.start()

        while search_timer.running:
            try:
                url = self.url[self.search_engine].format(self.target, len(self.results))
                resp = web_request(url, self.conn_timeout, self.proxies)
                http_code = get_statuscode(resp)

                if http_code != 200:
                    Log.info("{:<3} {} ({})".format(len(self.results), url, http_code))
                    Log.warn('None 200 response, exiting search ({})'.format(http_code))
                    break

                self.page_parser(resp)
                Log.info("{:<3} {} ({})".format(len(self.results), url, http_code))

                sleep(self.jitter)
            except KeyboardInterrupt:
                Log.warn("Key event detected, exiting search...")
                break

        search_timer.stop()
        return self.results

    def page_parser(self, resp):
        for link in extract_links(resp):
            try:
                self.results_handler(link)
            except Exception as e:
                Log.warn('Failed Parsing: {}- {}'.format(link.get('href'), e))

    def link_parser(self, url, link):
        u = {'url': url}
        u['text'] = unidecode(link.text.split("|")[0].split("...")[0])  # Capture link text before trailing chars
        u['title'] = self.parse_linkedin_title(u['text'])               # Extract job title
        u['fname'] = self.parse_linkedin_fname(u['text'])               # Extract first name
        u['lname'] = self.parse_linkedin_lname(u['text'])               # Extract last name
        return u

    def parse_linkedin_title(self, data):
        try:
            title = data.split("-")[1].split('https:')[0]
            return title.split("...")[0].split("|")[0].strip()
        except:
            return 'N/A'

    def parse_linkedin_fname(self, data):
        try:
            fname = data.split("-")[0].split(' ')[0].strip()
            return unidecode(fname)
        except:
            return False

    def parse_linkedin_lname(self, data):
        try:
            name = list(filter(None, data.split("-")[0].split(' ')))
            lname = name[-1].strip()
            return unidecode(lname[:-1]) if lname.endswith(".") else unidecode(lname)
        except:
            return False

    def results_handler(self, link):
        url = str(link.get('href')).lower()

        if extract_subdomain(url) not in ['www.linkedin.com']:
            return False
        elif 'linkedin.com/in' not in url:
            return False

        data = self.link_parser(url, link)
        if data['fname'] and data['lname']:
            self.log_results(data)

    def log_results(self, data):
        if data in self.results:
            return
        self.results.append(data)
        # Search results are logged to names.csv but names.txt is not generated until end to prevent duplicates
        logging.debug('  Fname: {:13} Lname: {:13} RawTxt: {}'.format(data['fname'], data['lname'], data['text']))
        csv.info('"{}","{}","{}","{}","{}","{}","{}",'.format(self.runtime, self.search_engine, data['fname'],
                                                           data['lname'], data['title'], data['url'], data['text']))


def get_statuscode(resp):
    try:
        return resp.status_code
    except:
        return 0


def get_proxy(proxies):
    tmp = choice(proxies) if proxies else False
    return {"http": tmp, "https": tmp} if tmp else {}


def get_agent():
    return choice([
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 12.5; rv:104.0) Gecko/20100101 Firefox/104.0',
        'Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 12_5_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0'
    ])


def web_request(url, timeout=3, proxies=[], **kwargs):
    try:
        s = requests.Session()
        r = requests.Request('GET', url, headers={'User-Agent': get_agent()}, **kwargs)
        p = r.prepare()
        return s.send(p, timeout=timeout, verify=False, proxies=get_proxy(proxies))
    except requests.exceptions.TooManyRedirects as e:
        Log.fail('Proxy Error: {}'.format(e))
    except:
        pass
    return False


def extract_links(resp):
    links = []
    soup = BeautifulSoup(resp.content, 'lxml')
    for link in soup.findAll('a'):
        links.append(link)
    return links


def extract_subdomain(url):
    return urlparse(url).netloc

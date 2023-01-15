#!/usr/bin/python3

import traceback
import logging
import requests
import json
from urllib.parse import urlparse
import re
from colorama import Fore, Style
import socket

mightyList = {}
networks = {}

startRegex = r"https?:\/{2}(?:[^\s\/]+\.)*"
endRegex = "(?:\/[^\s\/]+)*\/?"
torRegex = startRegex + "onion" + endRegex
i2pRegex = startRegex + "i2p" + endRegex
lokiRegex = startRegex + "loki" + endRegex
authRegex = r"https?:\/{2}\S+:\S+@(?:[^\s\/]+\.)*[a-zA-Z0-9]+" + endRegex

# 2.0 because Libredirect is currently on version 2.x.x
headers = {'User-Agent': 'Libredirect-instance-fetcher/2.0'}

with open('networks.json', 'rt') as tmp:
    networks = json.load(tmp)


def filterLastSlash(urlList):
    tmp = {}
    for frontend in urlList:
        tmp[frontend] = {}
        for network in urlList[frontend]:
            tmp[frontend][network] = []
            for url in urlList[frontend][network]:
                if url.endswith('/'):
                    tmp[frontend][network].append(url[:-1])
                    print(Fore.YELLOW + "Fixed " + Style.RESET_ALL + url)
                else:
                    tmp[frontend][network].append(url)
    return tmp


def idnaEncode(urlList):
    tmp = {}
    for frontend in urlList:
        tmp[frontend] = {}
        for network in urlList[frontend]:
            tmp[frontend][network] = []
            for url in urlList[frontend][network]:
                try:
                    encodedUrl = url.encode("idna").decode("utf8")
                    tmp[frontend][network].append(encodedUrl)
                    if (encodedUrl != url):
                        print(Fore.YELLOW + "Fixed " + Style.RESET_ALL + url)
                except Exception:
                    tmp[frontend][network].append(url)
    return tmp


def ip2bin(ip): return "".join(
    map(
        str,
        [
            "{0:08b}".format(int(x)) for x in ip.split(".")
        ]
    )
)


def get_cloudflare_ips():
    r = requests.get('https://www.cloudflare.com/ips-v4')
    return r.text.split('\n')


cloudflare_ips = get_cloudflare_ips()


def is_cloudflare(url):
    instance_ip = None
    try:
        instance_ip = socket.gethostbyname(urlparse(url).hostname)
        if instance_ip is None:
            return False
    except Exception:
        return False
    instance_bin = ip2bin(instance_ip)

    for cloudflare_ip_mask in cloudflare_ips:
        cloudflare_ip = cloudflare_ip_mask.split('/')[0]
        cloudflare_bin = ip2bin(cloudflare_ip)

        mask = int(cloudflare_ip_mask.split('/')[1])
        cloudflare_bin_masked = cloudflare_bin[:mask]
        instance_bin_masked = instance_bin[:mask]

        if cloudflare_bin_masked == instance_bin_masked:
            print(url + ' is behind ' + Fore.RED +
                  'cloudflare' + Style.RESET_ALL)
            return True
    return False


def is_authenticate(url):
    try:
        if re.match(authRegex, url):
            print(url + ' requires ' + Fore.RED +
                  'authentication' + Style.RESET_ALL)
            return True
        r = requests.get(url, timeout=5, headers=headers)
        if 'www-authenticate' in r.headers:
            print(url + ' requires ' + Fore.RED +
                  'authentication' + Style.RESET_ALL)
            return True
    except Exception:
        return False
    return False


def fetchCache(frontend, name):
    try:
        with open('./data.json') as file:
            mightyList[frontend] = json.load(file)[frontend]
        print(Fore.YELLOW + 'Failed' + Style.RESET_ALL + ' to fetch ' + name)
    except Exception:
        print(Fore.RED + 'Failed' + Style.RESET_ALL + ' to get cached ' + name)


def fetchFromFile(frontend, name):
    with open('./fixed/' + frontend + '.json') as file:
        mightyList[frontend] = json.load(file)
    print(Fore.GREEN + 'Fetched ' + Style.RESET_ALL + name)


def fetchJsonList(frontend, name, url, urlItem, jsonObject):
    try:
        r = requests.get(url, headers=headers)
        rJson = json.loads(r.text)
        if jsonObject:
            rJson = rJson['instances']
        _list = {}
        for network in networks:
            _list[network] = []
        if type(urlItem) == dict:
            for item in rJson:
                for network in networks:
                    if urlItem[network] is not None:
                        if urlItem[network] in item and item[urlItem[network]] is not None:
                            if item[urlItem[network]].strip() != '':
                                _list[network].append(item[urlItem[network]])
        else:
            for item in rJson:
                tmpItem = item
                if urlItem is not None:
                    tmpItem = item[urlItem]
                if tmpItem.strip() == '':
                    continue
                elif re.search(torRegex, tmpItem):
                    _list['tor'].append(tmpItem)
                elif re.search(i2pRegex, tmpItem):
                    _list['i2p'].append(tmpItem)
                elif re.search(lokiRegex, tmpItem):
                    _list['loki'].append(tmpItem)
                else:
                    _list['clearnet'].append(tmpItem)

        mightyList[frontend] = _list
        print(Fore.GREEN + 'Fetched ' + Style.RESET_ALL + name)
    except Exception:
        fetchCache(frontend, name)
        logging.error(traceback.format_exc())


def fetchRegexList(frontend, name, url, regex):
    try:
        r = requests.get(url, headers=headers)
        _list = {}
        for network in networks:
            _list[network] = []

        tmp = re.findall(regex, r.text)

        for item in tmp:
            if item.strip() == "":
                continue
            elif re.search(torRegex, item):
                _list['tor'].append(item)
            elif re.search(i2pRegex, item):
                _list['i2p'].append(item)
            elif re.search(lokiRegex, item):
                _list['loki'].append(item)
            else:
                _list['clearnet'].append(item)
        mightyList[frontend] = _list
        print(Fore.GREEN + 'Fetched ' + Style.RESET_ALL + name)
    except Exception:
        fetchCache(frontend, name)
        logging.error(traceback.format_exc())


def fetchTextList(frontend, name, url, prepend):
    try:
        _list = {}
        for network in networks:
            _list[network] = []

        if type(url) == dict:
            for network in networks:
                if url[network] is not None:
                    r = requests.get(url[network], headers=headers)
                    tmp = r.text.strip().split('\n')
                    for item in tmp:
                        item = prepend[network] + item
                        _list[network].append(item)
        else:
            r = requests.get(url, headers=headers)
            tmp = r.text.strip().split('\n')

            for item in tmp:
                item = prepend + item
                if re.search(torRegex, item):
                    _list['tor'].append(item)
                elif re.search(i2pRegex, item):
                    _list['i2p'].append(item)
                elif re.search(lokiRegex, item):
                    _list['loki'].append(item)
                else:
                    _list['clearnet'].append(item)
        mightyList[frontend] = _list
        print(Fore.GREEN + 'Fetched ' + Style.RESET_ALL + name)
    except Exception:
        fetchCache(frontend, name)
        logging.error(traceback.format_exc())


def invidious():
    name = 'Invidious'
    frontend = 'invidious'
    url = 'https://api.invidious.io/instances.json'
    try:
        _list = {}
        _list['clearnet'] = []
        _list['tor'] = []
        _list['i2p'] = []
        _list['loki'] = []
        r = requests.get(url, headers=headers)
        rJson = json.loads(r.text)
        for instance in rJson:
            if instance[1]['type'] == 'https':
                _list['clearnet'].append(instance[1]['uri'])
            elif instance[1]['type'] == 'onion':
                _list['tor'].append(instance[1]['uri'])
            elif instance[1]['type'] == 'i2p':
                _list['i2p'].append(instance[1]['uri'])
        mightyList[frontend] = _list
        print(Fore.GREEN + 'Fetched ' + Style.RESET_ALL + name)
    except Exception:
        fetchCache(frontend, name)
        logging.error(traceback.format_exc())


def piped():
    frontend = 'piped'
    name = 'Piped'
    try:
        _list = {}
        _list['clearnet'] = []
        _list['tor'] = []
        _list['i2p'] = []
        _list['loki'] = []
        r = requests.get(
            'https://raw.githubusercontent.com/wiki/TeamPiped/Piped/Instances.md', headers=headers)

        tmp = re.findall(
            r'(?:[^\s\/]+\.)+[a-zA-Z]+ (?:\(Official\) )?\| (https:\/{2}(?:[^\s\/]+\.)+[a-zA-Z]+) \| ', r.text)
        for item in tmp:
            try:
                url = requests.get(item, timeout=5, headers=headers).url
                if url.strip("/") == item:
                    continue
                else:
                    _list['clearnet'].append(url)
            except Exception:
                logging.error(traceback.format_exc())
                continue
        mightyList[frontend] = _list
        print(Fore.GREEN + 'Fetched ' + Style.RESET_ALL + name)
    except Exception:
        fetchCache(frontend, name)
        logging.error(traceback.format_exc())


def pipedMaterial():
    fetchRegexList('pipedMaterial', 'Piped-Material', 'https://raw.githubusercontent.com/mmjee/Piped-Material/master/README.md',
                   r"\| (https?:\/{2}(?:\S+\.)+[a-zA-Z0-9]*) +\| Production")


def cloudtube():
    fetchFromFile('cloudtube', 'Cloudtube')


def proxitok():
    fetchRegexList('proxiTok', 'ProxiTok', 'https://raw.githubusercontent.com/wiki/pablouser1/ProxiTok/Public-instances.md',
                   r"\| \[.*\]\(([-a-zA-Z0-9@:%_\+.~#?&//=]{2,}\.[a-z]{2,}\b(?:\/[-a-zA-Z0-9@:%_\+.~#?&//=]*)?)\)(?: \(Official\))? +\|(?:(?: [A-Z]*.*\|.*\|)|(?:$))")


def send():
    fetchRegexList('send', 'Send', 'https://gitlab.com/timvisee/send-instances/-/raw/master/README.md',
                   r"- ([-a-zA-Z0-9@:%_\+.~#?&//=]{2,}\.[a-z0-9]{2,}\b(?:\/[-a-zA-Z0-9@:%_\+.~#?&//=]*)?)\)*\|*[A-Z]{0,}")


def nitter():
    fetchRegexList('nitter', 'Nitter', 'https://raw.githubusercontent.com/wiki/zedeus/nitter/Instances.md',
                   r"(?:(?:\| )|(?:-   ))\[(?:(?:\S+\.)+[a-zA-Z0-9]+)\/?\]\((https?:\/{2}(?:\S+\.)+[a-zA-Z0-9]+)\/?\)(?:(?: (?:\((?:\S+ ?\S*)\) )? *\| [^❌]{1,4} +\|(?:(?:\n)|(?: ❌)|(?: ✅)|(?: ❓)|(?: \[)))|(?:\n))")


def bibliogram():
    fetchFromFile('bibliogram', 'Bibliogram')


def libreddit():
    fetchJsonList('libreddit', 'Libreddit', 'https://github.com/libreddit/libreddit-instances/raw/master/instances.json',
                  {'clearnet': 'url', 'tor': 'onion', 'i2p': 'i2p', 'loki': None}, True)


def teddit():
    fetchJsonList('teddit', 'Teddit', 'https://codeberg.org/teddit/teddit/raw/branch/main/instances.json',
                  {'clearnet': 'url', 'tor': 'onion', 'i2p': 'i2p', 'loki': None}, False)


def scribe():
    fetchJsonList('scribe', 'Scribe',
                  'https://git.sr.ht/~edwardloveall/scribe/blob/main/docs/instances.json', None, False)


def quetre():
    fetchRegexList('quetre', 'Quetre', 'https://raw.githubusercontent.com/zyachel/quetre/main/README.md',
                   r"\| \[.*\]\(([-a-zA-Z0-9@:%_\+.~#?&//=]{2,}\.[a-z0-9]{2,}\b(?:\/[-a-zA-Z0-9@:%_\+.~#?&//=]*)?)\)*\|*[A-Z]{0,}.*\|.*\|")


def libremdb():
    fetchRegexList('libremdb', 'libremdb', 'https://raw.githubusercontent.com/zyachel/libremdb/main/README.md',
                   r"\| \[.*\]\(([-a-zA-Z0-9@:%_\+.~#?&//=]{2,}\.[a-z0-9]{2,}\b(?:\/[-a-zA-Z0-9@:%_\+.~#?&//=]*)?)\)*\|*[A-Z]{0,}.*\|.*\|")


def simpleertube():
    fetchTextList('simpleertube', 'SimpleerTube', {'clearnet': 'https://simple-web.org/instances/simpleertube', 'tor': 'https://simple-web.org/instances/simpleertube_onion',
                  'i2p': 'https://simple-web.org/instances/simpleertube_i2p', 'loki': None}, {'clearnet': 'https://', 'tor': 'http://', 'i2p': 'http://', 'loki': 'http://'})


def simplytranslate():
    fetchTextList('simplyTranslate', 'SimplyTranslate', {'clearnet': 'https://simple-web.org/instances/simplytranslate', 'tor': 'https://simple-web.org/instances/simplytranslate_onion',
                  'i2p': 'https://simple-web.org/instances/simplytranslate_i2p', 'loki': 'https://simple-web.org/instances/simplytranslate_loki'}, {'clearnet': 'https://', 'tor': 'http://', 'i2p': 'http://', 'loki': 'http://'})


def linvgatranslate():
    fetchJsonList('lingva', 'LingvaTranslate',
                  'https://raw.githubusercontent.com/TheDavidDelta/lingva-translate/main/instances.json', None, False)


def searx_searxng():
    r = requests.get(
        'https://searx.space/data/instances.json', headers=headers)
    rJson = json.loads(r.text)
    searxList = {}
    searxList['clearnet'] = []
    searxList['tor'] = []
    searxList['i2p'] = []
    searxList['loki'] = []
    searxngList = {}
    searxngList['clearnet'] = []
    searxngList['tor'] = []
    searxngList['i2p'] = []
    searxngList['loki'] = []
    for item in rJson['instances']:
        if re.search(torRegex, item[:-1]):
            if (rJson['instances'][item].get('generator') == 'searxng'):
                searxngList['tor'].append(item[:-1])
            else:
                searxList['tor'].append(item[:-1])
        elif re.search(i2pRegex, item[:-1]):
            if (rJson['instances'][item].get('generator') == 'searxng'):
                searxngList['i2p'].append(item[:-1])
            else:
                searxList['i2p'].append(item[:-1])
        else:
            if (rJson['instances'][item].get('generator') == 'searxng'):
                searxngList['clearnet'].append(item[:-1])
            else:
                searxList['clearnet'].append(item[:-1])

    mightyList['searx'] = searxList
    mightyList['searxng'] = searxngList
    print(Fore.GREEN + 'Fetched ' + Style.RESET_ALL + 'SearX, SearXNG')


def whoogle():
    fetchRegexList('whoogle', 'Whoogle', 'https://raw.githubusercontent.com/benbusby/whoogle-search/main/README.md',
                   r"\| \[https?:\/{2}(?:[^\s\/]+\.)*(?:[^\s\/]+\.)+[a-zA-Z0-9]+\]\((https?:\/{2}(?:[^\s\/]+\.)*(?:[^\s\/]+\.)+[a-zA-Z0-9]+)\/?\) \| ")


def librex():
    fetchJsonList('librex', 'LibreX', 'https://raw.githubusercontent.com/hnhx/librex/main/instances.json',
                  {'clearnet': 'clearnet', 'tor': 'tor', 'i2p': 'i2p', 'loki': None}, True)


def rimgo():
    fetchJsonList('rimgo', 'rimgo', 'https://codeberg.org/video-prize-ranch/rimgo/raw/branch/main/instances.json',
                  {'clearnet': 'url', 'tor': 'onion', 'i2p': 'i2p', 'loki': None}, False)


def librarian():
    fetchJsonList('librarian', 'Librarian',
                  'https://codeberg.org/librarian/librarian/raw/branch/main/instances.json', 'url', True)


def beatbump():
    fetchFromFile('beatbump', 'Beatbump')


def hyperpipe():
    fetchJsonList('hyperpipe', 'Hyperpipe',
                  'https://codeberg.org/Hyperpipe/pages/raw/branch/main/api/frontend.json', 'url', False)


def facil():
    fetchFromFile('facil', 'FacilMap')


def osm():
    fetchFromFile('osm', 'OpenStreetMap')


def libreTranslate():
    fetchRegexList('libreTranslate', 'LibreTranslate', 'https://raw.githubusercontent.com/LibreTranslate/LibreTranslate/main/README.md',
                   r"\[(?:[^\s\/]+\.)+[a-zA-Z0-9]+\]\((https?:\/{2}(?:[^\s\/]+\.)+[a-zA-Z0-9]+)\/?\)\|")


def breezeWiki():
    fetchJsonList('breezeWiki', 'BreezeWiki',
                  'https://docs.breezewiki.com/files/instances.json', 'instance', False)


def privateBin():
    fetchJsonList('privateBin', 'PrivateBin',
                  'https://privatebin.info/directory/api?top=100&https_redirect=true&min_rating=A&csp_header=true&min_uptime=100&attachments=true', 'url', False)


def isValid(url):  # This code is contributed by avanitrachhadiya2155
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


invidious()
piped()
pipedMaterial()
cloudtube()
proxitok()
send()
nitter()
bibliogram()
libreddit()
teddit()
scribe()
quetre()
libremdb()
simplytranslate()
linvgatranslate()
libreTranslate()
searx_searxng()
whoogle()
librex()
rimgo()
librarian()
beatbump()
hyperpipe()
facil()
osm()
simpleertube()
breezeWiki()
privateBin()
mightyList = filterLastSlash(mightyList)
mightyList = idnaEncode(mightyList)

cloudflare = []
authenticate = []
for k1, v1 in mightyList.items():
    if type(mightyList[k1]) is dict:
        for k2, v2 in mightyList[k1].items():
            for instance in mightyList[k1][k2]:
                if (not isValid(instance)):
                    mightyList[k1][k2].remove(instance)
                    print("removed " + instance)
                else:
                    if not instance.endswith('.onion') and not instance.endswith('.i2p') and not instance.endswith('.loki') and is_cloudflare(instance):
                        cloudflare.append(instance)
                    if not instance.endswith('.onion') and not instance.endswith('.i2p') and not instance.endswith('.loki') and is_authenticate(instance):
                        authenticate.append(instance)
blacklist = {
    'cloudflare': cloudflare,
    'authenticate': authenticate,
}

# Writing to file
json_object = json.dumps(mightyList, ensure_ascii=False, indent=2)
with open('./data.json', 'w') as outfile:
    outfile.write(json_object)
print(Fore.BLUE + 'wrote ' + Style.RESET_ALL + 'instances/data.json')

json_object = json.dumps(blacklist, ensure_ascii=False, indent=2)
with open('./blacklist.json', 'w') as outfile:
    outfile.write(json_object)
print(Fore.BLUE + 'wrote ' + Style.RESET_ALL + 'instances/blacklist.json')

# print(json_object)

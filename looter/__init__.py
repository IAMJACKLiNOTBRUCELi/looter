"""Looter, a python package designed for web crawler lovers :)
Author: alphardex  QQ:2582347430
If any suggestion, please contact me. 
Thank you for cooperation!

Usage:
  looter genspider <name> <tmpl> [--async]
  looter shell [<url>]
  looter (-h | --help | --version)

Options:
  -h --help        Show this screen.
  --version        Show version.
  --async          Use async instead of concurrent.
"""
import os
import json
import code
import re
import time
import uuid
import webbrowser
import functools
from operator import itemgetter
from urllib.parse import unquote
import asyncio
import aiohttp
import requests
from lxml import etree
from fake_useragent import UserAgent
from docopt import docopt

VERSION = '1.61'
UA = UserAgent()

BANNER = """
Available objects:
    url           The url of the site you crawled.
    res           The response of the site.
    tree          The source tree, can be parsed by xpath and cssselect.

Available functions:
    fetch         Get the element tree of an HTML page.
    view          View the page in your browser. (test rendering)
    links         Get all the links of the page.
    alexa_rank    Get the reach and popularity of a site in alexa.
    save_imgs     Save the images you crawled.
    save_as_json  Save what you crawled as a json file.

For more info, plz refer to tutorial:
    [cssselect]: http://www.runoob.com/cssref/css-selectors.html
    [xpath]: http://www.runoob.com/xpath/xpath-syntax.html
"""


def perf(f):
    """
    A decorator to measure the performance of a specific function.
    """
    @functools.wraps(f)
    def wr(*args, **kwargs):
        start = time.time()
        r = f(*args, **kwargs)
        end = time.time()
        print(f'Time elapsed: {end - start}')
        return r
    return wr


def send_request(url: str, timeout=60) -> requests.models.Response:
    """Send an HTTP request to a url.
    
    Args:
        url (str): The url of the site.
        timeout (int, optional): Defaults to 60. The maxium time of request.

    Returns:
        requests.models.Response: The response of the HTTP request.
    """
    headers = {'User-Agent': UA.random}
    try:
        res = requests.get(url, headers=headers, timeout=timeout)
        res.raise_for_status()
    except requests.exceptions.MissingSchema:
        res = requests.get('http://' + url, headers=headers, timeout=timeout)
    return res


def fetch(url: str):
    """
    Get the element tree of an HTML page, use cssselect or xpath to parse it.

    Please refer to the tutorial of this module, and selector tutorial below:
        cssselect: http://www.runoob.com/cssref/css-selectors.html
        xpath: http://www.runoob.com/xpath/xpath-syntax.html

    Args:
        url (str): The url of the site.
    
    Returns:
        The element tree of html.
    """
    res = send_request(url)
    html = res.text
    tree = etree.HTML(html)
    return tree


def view(url: str, encoding='utf-8', name='test'):
    """
    View the page whether rendered properly. (Usually for testing purpose)

    Args:
        url (str): The url of the site.
        encoding (str, optional): Defaults to 'utf-8'. The encoding of the file.
        name (str, optional): Defaults to 'test'. The name of the file.
    """
    with open(f'{name}.html', 'w', encoding=encoding) as f:
        f.write(send_request(url).text)
    webbrowser.open(f'{name}.html', new=1)


def rectify(name: str) -> str:
    """
    Get rid of illegal symbols of a filename.

    Args:
        name (str): The filename.

    Returns:
        The rectified filename.
    """
    if any(symbol in name for symbol in ['?', '<', '>', '|', '*', '"', ":"]):
        name = ''.join([c for c in name if c not in {
            '?', '<', '>', '|', '*', '"', ":"}])
    return unquote(name)


def get_img_name(url: str, max_length=160) -> str:
    """Get the name of an image.

    Args:
        url (str): The url of the site.
        max_length (int, optional): Defaults to 160. The maximal length of the filename.

    Returns:
        The name of an image and its url.
    """
    if hasattr(url, 'tag') and url.tag == 'a':
        url = url.get('href')
    elif hasattr(url, 'tag') and url.tag == 'img':
        url = url.get('src')
    name = rectify(url.split('/')[-1])
    ext = name.split('.')[-1]
    name = f"{name[:max_length]}.{ext}"
    name = name[:-4] if name.endswith(f'.{ext}.{ext}') else name
    return url, name


@perf
def save_img(url: str, random_name=False):
    """
    Download image and save it to local disk.

    Args:
        url (str): The url of the site.
        random_name (int, optional): Defaults to False. If names of images are duplicated, use this.
    """
    headers = {'User-Agent': UA.random}
    url, name = get_img_name(url)
    if random_name:
        name = f'{name[:-4]}{str(uuid.uuid4())[:8]}{name[-4:]}'
    with open(name, 'wb') as f:
        url = url if url.startswith('http') else f'http:{url}'
        f.write(requests.get(url, headers=headers).content)
        print(f'Saved {name}')


def save_imgs(urls, random_name=False):
    """
    Download images from links.
    """
    return [save_img(url, random_name=random_name) for url in urls]


def alexa_rank(url: str) -> tuple:
    """
    Get the reach and popularity of a site in alexa.
    It will return a tuple:
    (url, reach_rank, popularity_rank)

    Args:
        url (str): The url of the site.

    Returns:
        tuple: (url, reach_rank, popularity_rank)
    """
    alexa = f'http://data.alexa.com/data?cli=10&dat=snbamz&url={url}'
    page = send_request(alexa).text
    reach_rank = re.findall(r'REACH[^\d]*(\d+)', page)
    popularity_rank = re.findall(r'POPULARITY[^\d]*(\d+)', page)
    if reach_rank and popularity_rank:
        print(f'[{url}] REACH: {reach_rank[0]} POPULARITY: {popularity_rank[0]}')
        return url, reach_rank[0], popularity_rank[0]
    else:
        print(f'[{url}] Get rank failed.')
        return None


async def async_fetch(url: str, res_type='text'):
    """Fetch a webpage in an async style.

    Args:
        url: The url of the site.
        res_type: The type of response: text, content

    Returns:
        The element tree of the HTML page.
    """
    headers = {'User-Agent': UA.random}
    async with aiohttp.ClientSession() as ses:
        async with ses.get(url, headers=headers) as res:
            html = await res.text() if res_type == 'text' else res.read()
            tree = etree.HTML(html)
            return tree


async def async_save_img(url: str, random_name=False):
    """Save an image in an async style.

    Args:
        url (str): The url of the site.
        random_name (int, optional): Defaults to False. If names of images are duplicated, use this.
    """
    headers = {'User-Agent': UA.random}
    url, name = get_img_name(url)
    url = url if url.startswith('http') else f'http:{url}'
    if random_name:
        name = f'{name[:-4]}{str(uuid.uuid4())[:8]}{name[-4:]}'
    with open(name, 'wb') as f:
        async with aiohttp.ClientSession() as ses:
            async with ses.get(url, headers=headers) as res:
                data = await res.read()
                f.write(data)
                print(f'Saved {name}')


def async_save_imgs(urls: str, random_name=False):
    """
    Download images from links in an async style.
    """
    loop = asyncio.get_event_loop()
    result = [async_save_img(url, random_name=random_name) for url in urls]
    loop.run_until_complete(asyncio.wait(result))
    loop.close()


def links(res: requests.models.Response, search=None, absolute=False) -> list:
    """Get all the links of the page.
    
    Args:
        res (requests.models.Response): The response of the page.
        search ([type], optional): Defaults to None. Search the links you want.
        absolute (bool, optional): Defaults to False. Get the absolute links.
    
    Returns:
        list: All the links of the page.
    """
    domain = res.url
    tree = etree.HTML(res.text)
    hrefs = [link.get('href')
             for link in tree.cssselect('a') if link.get('href')]
    if search:
        hrefs = [href for href in hrefs if search in href]
    if absolute:
        hrefs = [domain + href for href in hrefs if not href.startswith('http')]
    return hrefs


def save_as_json(total: list, name='data', sort_by=None):
    """Save what you crawled as a json file.
    
    Args:
        total (list): Total of data you crawled.
        name (str, optional): Defaults to 'data'. The name of the json file.
        sort_by ([type], optional): Defaults to None. Sort items by a specific key.
    """
    if sort_by:
        total = sorted(total, key=itemgetter(sort_by))
    with open(f'{name}.json', 'w', encoding='utf-8') as f:
        f.write(json.dumps(total, ensure_ascii=False))


def cli():
    """
    Commandline for looter!
    """
    argv = docopt(__doc__, version=VERSION)
    if argv['genspider']:
        template = argv['<tmpl>']
        name = argv['<name>']
        async_ = argv['--async']
        if template not in ['data', 'image']:
            exit('Plz provide a template (data, image)')
        if async_:
            template = template + '_async'
        package_path = os.path.dirname(__file__)
        with open(f'{package_path}\\templates\\{template}.tmpl', 'r') as i, open(f'{name}.py', 'w') as o:
            o.write(i.read())

    if argv['shell']:
        if not argv['<url>']:
            url = input('Which site do u want to crawl?\nurl: ')
        else:
            url = argv['<url>']
        res = send_request(url)
        tree = etree.HTML(res.text)
        allvars = {**locals(), **globals()}
        code.interact(local=allvars, banner=BANNER)


if __name__ == '__main__':
    cli()

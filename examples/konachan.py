import looter as lt
from concurrent import futures

domain = 'https://konachan.net'

def crawl(url):
    src = lt.get_source(url)
    links = src.cssselect('a.directlink')
    lt.save_imgs(links)


if __name__ == '__main__':
    tasklist = list(f'{domain}/post?page={i}' for i in range(1, 9777))
    with futures.ThreadPoolExecutor(20) as executor:
        executor.map(crawl, tasklist)
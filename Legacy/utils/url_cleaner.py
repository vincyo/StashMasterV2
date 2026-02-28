import re
import requests
from urllib.parse import urlparse

def normalize_url(url):
    url = url.strip()
    url = re.sub(r'^https?://(www\.)?', '', url.lower())
    return url

def is_valid_url(url):
    if not url.startswith('http'):
        return False
    if 'wikipedia.org' in url and not url.startswith('https://en.wikipedia.org'):
        return False
    blacklist = ['google.com', 'bing.com']
    for b in blacklist:
        if b in url:
            return False
    return True

def check_link_health(url, timeout=2):
    try:
        resp = requests.head(url, timeout=timeout, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
        return resp.status_code < 400
    except Exception:
        return False

def categorize_links(urls, skip_health_check_urls=None):
    if skip_health_check_urls is None:
        skip_health_check_urls = set()
    seen = set()
    valid_final = []
    rejected = []
    for url in urls:
        if not url.strip():
            continue
        norm = normalize_url(url)
        if norm in seen:
            continue
        seen.add(norm)
        if not is_valid_url(url):
            rejected.append(url)
            continue
        if url in skip_health_check_urls:
            valid_final.append(url)
            continue
        if not check_link_health(url):
            rejected.append(url)
            continue
        valid_final.append(url)
    # Tri par priorité
    site_domains = ['iafd.com', 'babepedia.com', 'wikidata.org', 'boobpedia.com',
                   'imdb.com', 'themoviedb.org', 'freeones.com', 'thenude.com']
    social_domains = ['twitter.com', 'x.com', 'instagram.com', 'onlyfans.com',
                     'facebook.com', 'tiktok.com', 'twitch.tv', 'youtube.com']
    def domain_priority(url):
        d = urlparse(url).netloc
        for i, dom in enumerate(site_domains):
            if dom in d:
                return i
        if any(s in d for s in social_domains):
            return 100 + sorted(social_domains).index([s for s in social_domains if s in d][0])
        return 99
    valid_final = sorted(valid_final, key=domain_priority)
    return valid_final, rejected

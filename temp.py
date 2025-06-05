import requests
from urllib.parse import urlparse, parse_qs, unquote

def extrair_redirect_url_recursiva(url):
    while True:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        if 'redirectUrl' in query_params:
            redirect_url = unquote(query_params['redirectUrl'][0])
            if 'aliexpress.com/item/' in redirect_url:
                return redirect_url
            url = redirect_url
        else:
            return url

def resolver_link_ali(link_encurtado, max_redirects=5):
    url = link_encurtado
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0'}
    redirects = 0

    while redirects < max_redirects:
        response = session.head(url, allow_redirects=False, headers=headers)
        if 300 <= response.status_code < 400 and 'Location' in response.headers:
            url = response.headers['Location']
            redirects += 1
        else:
            break
    url_final = extrair_redirect_url_recursiva(url)
    return url_final

link_curto = "https://s.click.aliexpress.com/e/_m0PidlV"
print(resolver_link_ali(link_curto))

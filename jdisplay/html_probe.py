from html.parser import HTMLParser
import urllib.request

class TitleParser(HTMLParser):
    def __init__(self): super().__init__(); self._in=False; self.title=""
    def handle_starttag(self, tag, attrs): self._in = (tag=="title")
    def handle_endtag(self, tag): 
        if tag=="title": self._in=False
    def handle_data(self, data):
        if self._in: self.title += data.strip()

def fetch_title(url: str) -> str|None:
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            html = r.read().decode("utf-8", "ignore")
        p = TitleParser(); p.feed(html)
        return p.title or None
    except Exception:
        return None

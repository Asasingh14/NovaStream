from src.scraper import find_episode_links

class DummyResp:
    def __init__(self, text):
        self.text = text
    def raise_for_status(self):
        pass

def test_find_episode_links_static(monkeypatch):
    html = '<a href="/show/episode-1">1</a><a href="episode_2/">2</a>'
    monkeypatch.setattr('src.scraper.requests.get', lambda *args, **kwargs: DummyResp(html))
    links = find_episode_links('https://example.com')
    assert links == [
        (1, 'https://example.com/show/episode-1'),
        (2, 'https://example.com/episode_2/')
    ]

def test_find_episode_links_fallback(monkeypatch):
    # Static parse yields no links
    monkeypatch.setattr('src.scraper.requests.get', lambda *args, **kwargs: DummyResp(''))
    class DummyDriver:
        def __init__(self):
            self.page_source = '<a href="ep-10/">10</a>'
        def get(self, url):
            pass
        def quit(self):
            pass
    monkeypatch.setattr('src.scraper.get_driver', lambda: DummyDriver())
    links = find_episode_links('https://test.com')
    assert links == [
        (10, 'https://test.com/ep-10/')
    ]

def test_find_episode_links_none(monkeypatch):
    # No links and fallback driver raises
    monkeypatch.setattr('src.scraper.requests.get', lambda *args, **kwargs: DummyResp(''))
    def bad_driver():
        raise Exception('no driver')
    monkeypatch.setattr('src.scraper.get_driver', bad_driver)
    links = find_episode_links('https://none/')
    assert links == [] 
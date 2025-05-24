import pytest
import time
from src.manifest import get_manifest_urls
import src.manifest as manifest_mod

class DummyReq:
    def __init__(self, url, headers):
        self.url = url
        self.response = type('R', (), {'headers': headers})

class DummyDriver:
    def __init__(self):
        self.requests = [
            DummyReq('http://x/media.m3u8', {}),
            DummyReq('http://x/other.ts', {}),
            DummyReq('http://x/stream1', {'content-type': 'application/vnd.apple.mpegurl'})
        ]
    def get(self, url):
        pass
    def execute_script(self, script):
        pass
    def quit(self):
        pass

def test_get_manifest_urls_filters(monkeypatch):
    # Patch Chrome driver and sleep
    monkeypatch.setattr('seleniumwire.webdriver.Chrome', lambda *args, **kwargs: DummyDriver(), raising=True)
    monkeypatch.setattr(time, 'sleep', lambda x: None)
    manifests = get_manifest_urls('http://test', wait=0)
    assert 'http://x/media.m3u8' in manifests
    assert 'http://x/stream1' in manifests
    assert 'http://x/other.ts' not in manifests

# Edge: no requests
class EmptyDriver(DummyDriver):
    def __init__(self):
        self.requests = []

def test_get_manifest_urls_empty(monkeypatch):
    monkeypatch.setattr('seleniumwire.webdriver.Chrome', lambda *args, **kwargs: EmptyDriver(), raising=True)
    monkeypatch.setattr(time, 'sleep', lambda x: None)
    manifests = get_manifest_urls('http://none', wait=0)
    assert manifests == set() 
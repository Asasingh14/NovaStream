import time
from src.manifest import get_manifest_urls
import sys
import types

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

def test_get_manifest_urls_autoplay_exception(monkeypatch, capsys):
    """
    Test that if execute_script throws, we catch and print a warning, and still return manifests.
    """
    # Prepare DummyDriver that raises on execute_script
    class DummyDriverExec(DummyDriver):
        def execute_script(self, script):
            raise Exception('no video')
    # Patch seleniumwire.webdriver.Chrome
    sw_pkg = types.ModuleType('seleniumwire')
    sw_pkg.__path__ = []
    sw_wd = types.ModuleType('seleniumwire.webdriver')
    sw_wd.Chrome = lambda *args, **kwargs: DummyDriverExec()
    sys.modules['seleniumwire'] = sw_pkg
    sys.modules['seleniumwire.webdriver'] = sw_wd
    # Patch selenium.webdriver.chrome.options.Options
    selenium_pkg = types.ModuleType('selenium')
    selenium_pkg.__path__ = []
    sys.modules['selenium'] = selenium_pkg
    sys.modules['selenium.webdriver'] = types.ModuleType('selenium.webdriver')
    sys.modules['selenium.webdriver.chrome'] = types.ModuleType('selenium.webdriver.chrome')
    opts_mod = types.ModuleType('selenium.webdriver.chrome.options')
    class DummyOptions:
        def __init__(self): self.args = []
        def add_argument(self, arg): self.args.append(arg)
    opts_mod.Options = DummyOptions
    sys.modules['selenium.webdriver.chrome.options'] = opts_mod
    # Patch time.sleep
    monkeypatch.setattr(sys.modules['time'], 'sleep', lambda x: None)
    # Run and capture
    manifests = get_manifest_urls('http://test', wait=0)
    captured = capsys.readouterr()
    # Warning printed from execute_script exception
    assert 'Warning: Failed to auto-play video' in captured.out
    # Should still filter manifests from DummyDriverExec.requests
    assert 'http://x/media.m3u8' in manifests
    assert 'http://x/stream1' in manifests
    assert 'http://x/other.ts' not in manifests 
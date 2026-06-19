import time
from threading import Event
import pytest
from src.manifest import get_manifest_urls

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
    monkeypatch.setattr('src.manifest.get_driver', lambda: DummyDriver())
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
    monkeypatch.setattr('src.manifest.get_driver', lambda: EmptyDriver())
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
    monkeypatch.setattr('src.manifest.get_driver', lambda: DummyDriverExec())
    # Patch time.sleep
    monkeypatch.setattr(time, 'sleep', lambda x: None)
    # Run and capture
    manifests = get_manifest_urls('http://test', wait=0)
    captured = capsys.readouterr()
    # Warning printed from execute_script exception
    assert 'Warning: Failed to auto-play video' in captured.out
    # Should still filter manifests from DummyDriverExec.requests
    assert 'http://x/media.m3u8' in manifests
    assert 'http://x/stream1' in manifests
    assert 'http://x/other.ts' not in manifests


def test_get_manifest_urls_closes_driver_when_navigation_fails(monkeypatch):
    driver = DummyDriver()
    closed = {'value': False}
    driver.get = lambda _url: (_ for _ in ()).throw(RuntimeError('navigation failed'))
    driver.quit = lambda: closed.update(value=True)
    monkeypatch.setattr('src.manifest.get_driver', lambda: driver)

    with pytest.raises(RuntimeError, match='navigation failed'):
        get_manifest_urls('http://test', wait=0)

    assert closed['value'] is True


def test_get_manifest_urls_returns_before_start_when_cancelled(monkeypatch):
    control = type('Control', (), {'cancelled': Event()})()
    control.cancelled.set()
    monkeypatch.setattr(
        'src.manifest.get_driver',
        lambda: pytest.fail('driver should not start after cancellation'),
    )

    assert get_manifest_urls('http://test', control=control) == set()


def test_get_manifest_urls_suppresses_shutdown_errors_after_cancel(monkeypatch):
    cancelled = Event()
    closed = {'value': False}

    class Control:
        def __init__(self):
            self.cancelled = cancelled

        def register_driver(self, _driver):
            pass

        def unregister_driver(self, _driver):
            pass

    class CancellingDriver(DummyDriver):
        def set_page_load_timeout(self, _timeout):
            cancelled.set()
            raise RuntimeError('driver closed during cancellation')

        def quit(self):
            closed['value'] = True

    monkeypatch.setattr('src.manifest.get_driver', lambda: CancellingDriver())

    assert get_manifest_urls('http://test', control=Control()) == set()
    assert closed['value'] is False

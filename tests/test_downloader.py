from src.downloader import download_episode
import src.downloader as dlmod
import pytest

class DummyRes:
    def __init__(self, code):
        self.returncode = code

class DummyPopen:
    def __init__(self, *args, **kwargs):
        self.returncode = 0
    def communicate(self):
        return (b'', b'')

def test_download_episode_no_manifest(tmp_path, capsys, monkeypatch):
    # No manifests => error message
    monkeypatch.setattr(dlmod.requests, 'get', lambda *args, **kwargs: (_ for _ in ()).throw(dlmod.requests.RequestException()))
    monkeypatch.setattr(dlmod, 'get_manifest_urls', lambda url: set())
    args = ('Show', 1, 'http://x', str(tmp_path))
    download_episode(args)
    captured = capsys.readouterr()
    assert '[#1]' in captured.out and 'No manifest found' in captured.out


def test_download_episode_skip_existing(tmp_path, capsys, monkeypatch):
    # Manifest present but file exists => skip
    monkeypatch.setattr(dlmod, 'get_manifest_urls', lambda url: {'http://x/media.m3u8'})
    monkeypatch.setattr(dlmod.requests, 'get', lambda *args, **kwargs: (_ for _ in ()).throw(dlmod.requests.RequestException()))
    # Create existing file matching new naming scheme
    filename = tmp_path / 'Show - Episode 01 - Episode 1.mp4'
    filename.write_text('')
    args = ('Show', 1, 'http://x', str(tmp_path))
    download_episode(args)
    captured = capsys.readouterr()
    assert 'Skipping download' in captured.out


def test_download_episode_success(tmp_path, capsys, monkeypatch):
    # Manifest present and file not exists => download
    monkeypatch.setattr(dlmod, 'get_manifest_urls', lambda url: {'http://x/media.m3u8'})
    monkeypatch.setattr(dlmod.requests, 'get', lambda *args, **kwargs: (_ for _ in ()).throw(dlmod.requests.RequestException()))
    # Stub subprocess.Popen to succeed
    monkeypatch.setattr(dlmod.subprocess, 'Popen', DummyPopen)
    args = ('Show', 2, 'http://x', str(tmp_path))
    download_episode(args)
    captured = capsys.readouterr()
    assert 'Download complete' in captured.out


def test_download_episode_retry_success(tmp_path, capsys, monkeypatch):
    # Manifest present, first ffmpeg fails then retry succeeds
    monkeypatch.setattr(dlmod, 'get_manifest_urls', lambda url: {'http://x/media.m3u8'})
    monkeypatch.setattr(dlmod.requests, 'get', lambda *args, **kwargs: (_ for _ in ()).throw(dlmod.requests.RequestException()))
    call = {'count': 0}
    class DummyPopenSeq:
        def __init__(self, *args, **kwargs):
            idx = call['count']
            call['count'] += 1
            self.returncode = 1 if idx == 0 else 0
        def communicate(self):
            return (b'', b'error' if self.returncode != 0 else b'')
    monkeypatch.setattr(dlmod.subprocess, 'Popen', DummyPopenSeq)
    args = ('Show', 3, 'http://x', str(tmp_path), 0, 1)
    result = download_episode(args)
    captured = capsys.readouterr()
    assert 'retry 1/1' in captured.out
    assert 'Download complete on retry 1' in captured.out
    assert result


def test_download_episode_retry_failure(tmp_path, capsys, monkeypatch):
    # Manifest present, ffmpeg always fails
    monkeypatch.setattr(dlmod, 'get_manifest_urls', lambda url: {'http://x/media.m3u8'})
    monkeypatch.setattr(dlmod.requests, 'get', lambda *args, **kwargs: (_ for _ in ()).throw(dlmod.requests.RequestException()))
    class DummyPopenFail:
        def __init__(self, *args, **kwargs):
            self.returncode = 1
        def communicate(self):
            return (b'', b'fail')
    monkeypatch.setattr(dlmod.subprocess, 'Popen', DummyPopenFail)
    args = ('Show', 4, 'http://x', str(tmp_path), 0, 2)
    result = download_episode(args)
    captured = capsys.readouterr()
    assert 'retry 1/2' in captured.out
    assert 'retry 2/2' in captured.out
    assert 'Download failed after 2 retries' in captured.out
    assert result is False


def test_download_episode_title_extract(tmp_path, capsys, monkeypatch):
    # Manifest present and title extracted from HTML
    monkeypatch.setattr(dlmod, 'get_manifest_urls', lambda url: {'http://x/media.m3u8'})
    class DummyResponse:
        def __init__(self, text):
            self.text = text
        def raise_for_status(self): pass
    monkeypatch.setattr(dlmod.requests, 'get', lambda *args, **kwargs: DummyResponse('<html><head><title>My Title![]</title></head></html>'))
    class DummyPopen2:
        def __init__(self, *args, **kwargs):
            self.returncode = 0
        def communicate(self):
            return (b'', b'')
    monkeypatch.setattr(dlmod.subprocess, 'Popen', DummyPopen2)
    args = ('Hey_You', 5, 'http://x', str(tmp_path))
    result = download_episode(args)
    captured = capsys.readouterr()
    assert 'Hey You - Episode 05 - My Title.mp4' in captured.out
    assert 'Download complete' in captured.out
    assert result


def test_download_episode_manifest_error(tmp_path, capsys, monkeypatch):
    # get_manifest_urls raises error
    monkeypatch.setattr(dlmod, 'get_manifest_urls', lambda url: (_ for _ in ()).throw(Exception('oops')))
    monkeypatch.setattr(dlmod.requests, 'get', lambda *args, **kwargs: (_ for _ in ()).throw(dlmod.requests.RequestException()))
    args = ('Show', 6, 'http://x', str(tmp_path))
    result = download_episode(args)
    captured = capsys.readouterr()
    assert 'Manifest retrieval error' in captured.out
    assert result is False


def test_download_episode_invalid_args():
    with pytest.raises(ValueError):
        download_episode(('bad', 'args')) 
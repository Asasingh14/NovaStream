from src.downloader import download_episode, run_download
import src.downloader as dlmod
import pytest
import logging

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

def test_safe_download_episode_success(monkeypatch):
    # _safe_download_episode should propagate return values
    monkeypatch.setattr(dlmod, 'download_episode', lambda args: 'ok')
    assert dlmod._safe_download_episode(('any',)) == 'ok'

def test_safe_download_episode_exception(monkeypatch, caplog):
    # _safe_download_episode should catch exceptions and return False
    monkeypatch.setattr(dlmod, 'download_episode', lambda args: (_ for _ in ()).throw(Exception('err')))
    caplog.set_level(logging.ERROR)
    result = dlmod._safe_download_episode(('any',))
    assert result is False
    assert 'Error in download_episode' in caplog.text

def test_run_download_single_episode(tmp_path, monkeypatch):
    # Test single-episode URL branch
    url = 'http://example.com/episode-5'
    name_input = 'My Show'
    monkeypatch.setattr(dlmod, 'banner', lambda: None)
    # Stub multiprocessing pool
    class DummyPool:
        def __init__(self, workers): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): pass
        def imap_unordered(self, func, args_list): return [None for _ in args_list]
    monkeypatch.setattr(dlmod.mp, 'Pool', DummyPool)
    # Stub tqdm to no-op
    monkeypatch.setattr(dlmod, 'tqdm', lambda it, total=None, desc=None: it)
    # Stub Tk and messagebox
    class DummyTk:
        def withdraw(self): pass
        def destroy(self): pass
    monkeypatch.setattr(dlmod.tk, 'Tk', DummyTk)
    info = {}
    monkeypatch.setattr(dlmod.messagebox, 'showinfo', lambda title, msg: info.update({'msg': msg}))
    run_download(url, name_input, str(tmp_path), download_all=False, episode_list=[], workers=1)
    # Expect one file saved
    assert '1 files saved' in info.get('msg', '')
    assert str(tmp_path.joinpath('My_Show')) in info.get('msg', '')

def test_run_download_no_episodes_error(tmp_path, monkeypatch):
    # No episodes found and no selection provided
    url = 'http://example.com/'
    monkeypatch.setattr(dlmod, 'banner', lambda: None)
    monkeypatch.setattr(dlmod, 'find_episode_links', lambda x: [])
    class DummyTk:
        def withdraw(self): pass
        def destroy(self): pass
    monkeypatch.setattr(dlmod.tk, 'Tk', DummyTk)
    err = {}
    monkeypatch.setattr(dlmod.messagebox, 'showerror', lambda title, msg: err.update({'msg': msg}))
    result = run_download(url, None, str(tmp_path), download_all=False, episode_list=[], workers=1)
    assert 'No episodes found' in err.get('msg', '')
    assert result is None

def test_run_download_download_all_no_input(tmp_path, monkeypatch):
    # download_all True but user cancels input => returns None
    url = 'http://example.com/'
    monkeypatch.setattr(dlmod, 'banner', lambda: None)
    monkeypatch.setattr(dlmod, 'find_episode_links', lambda x: [])
    monkeypatch.setattr(dlmod.simpledialog, 'askstring', lambda *args, **kwargs: None)
    class DummyTk:
        def withdraw(self): pass
        def destroy(self): pass
    monkeypatch.setattr(dlmod.tk, 'Tk', DummyTk)
    result = run_download(url, None, str(tmp_path), download_all=True, episode_list=[], workers=1)
    assert result is None

def test_run_download_download_all_with_input(tmp_path, monkeypatch):
    # download_all True with user input => processes episodes
    url = 'http://example.com/'
    monkeypatch.setattr(dlmod, 'banner', lambda: None)
    monkeypatch.setattr(dlmod, 'find_episode_links', lambda x: [])
    monkeypatch.setattr(dlmod.simpledialog, 'askstring', lambda *args, **kwargs: '2')
    class DummyTk:
        def withdraw(self): pass
        def destroy(self): pass
    monkeypatch.setattr(dlmod.tk, 'Tk', DummyTk)
    # Stub pool and tqdm and showinfo
    class DummyPool2:
        def __init__(self, w): pass
        def __enter__(self): return self
        def __exit__(self, a,b,c): pass
        def imap_unordered(self, func, args_list): return [None]*len(args_list)
    monkeypatch.setattr(dlmod.mp, 'Pool', DummyPool2)
    monkeypatch.setattr(dlmod, 'tqdm', lambda it, total=None, desc=None: it)
    info2 = {}
    monkeypatch.setattr(dlmod.messagebox, 'showinfo', lambda title, msg: info2.update({'msg': msg}))
    run_download(url, None, str(tmp_path), download_all=True, episode_list=[], workers=1)
    assert '2 files saved' in info2.get('msg', '')
    assert str(tmp_path.joinpath('example_com')) in info2.get('msg', '')

def test_run_download_with_episode_list(tmp_path, monkeypatch):
    # episode_list branch when find_episode_links empty
    url = 'http://example.com/'
    monkeypatch.setattr(dlmod, 'banner', lambda: None)
    monkeypatch.setattr(dlmod, 'find_episode_links', lambda x: [])
    # Override expand_ranges to specific list
    monkeypatch.setattr(dlmod, 'expand_ranges', lambda lst: [1,3])
    monkeypatch.setattr(dlmod.simpledialog, 'askstring', lambda *args, **kwargs: None)
    class DummyTk:
        def withdraw(self): pass
        def destroy(self): pass
    monkeypatch.setattr(dlmod.tk, 'Tk', DummyTk)
    class DummyPool3:
        def __init__(self, w): pass
        def __enter__(self): return self
        def __exit__(self, a,b,c): pass
        def imap_unordered(self, func, args_list): return [None]*len(args_list)
    monkeypatch.setattr(dlmod.mp, 'Pool', DummyPool3)
    monkeypatch.setattr(dlmod, 'tqdm', lambda it, total=None, desc=None: it)
    info3 = {}
    monkeypatch.setattr(dlmod.messagebox, 'showinfo', lambda title, msg: info3.update({'msg': msg}))
    run_download(url, None, str(tmp_path), download_all=False, episode_list=['1-3'], workers=1)
    assert '2 files saved' in info3.get('msg', '')
    assert str(tmp_path.joinpath('example_com')) in info3.get('msg', '')

def test_download_episode_failure_no_retries(tmp_path, capsys, monkeypatch):
    # Manifest present but ffmpeg fails and no retries => error and final failure
    monkeypatch.setattr(dlmod, 'get_manifest_urls', lambda url: {'http://x/media.m3u8'})
    monkeypatch.setattr(dlmod.requests, 'get', lambda *args, **kwargs: (_ for _ in ()).throw(dlmod.requests.RequestException()))
    class DummyPopenErr:
        def __init__(self, *args, **kwargs):
            self.returncode = 1
        def communicate(self):
            return (b'', b'fatal error')
    monkeypatch.setattr(dlmod.subprocess, 'Popen', DummyPopenErr)
    result = download_episode(('Show', 7, 'http://x', str(tmp_path)))
    captured = capsys.readouterr()
    assert result is False
    assert 'ffmpeg error:' in captured.out
    assert 'Download failed after 0 retries' in captured.out

def test_download_episode_no_title(tmp_path, capsys, monkeypatch):
    # HTML missing title tag falls back to default
    html = '<html><head></head><body></body></html>'
    class DummyResponse2:
        def __init__(self, text): self.text = text
        def raise_for_status(self): pass
    monkeypatch.setattr(dlmod.requests, 'get', lambda *args, **kwargs: DummyResponse2(html))
    monkeypatch.setattr(dlmod, 'get_manifest_urls', lambda url: {'http://x/media.m3u8'})
    class DummyPopenOK2:
        def __init__(self, *args, **kwargs): self.returncode = 0
        def communicate(self): return (b'', b'')
    monkeypatch.setattr(dlmod.subprocess, 'Popen', DummyPopenOK2)
    result = download_episode(('Show', 8, 'http://x', str(tmp_path)))
    captured = capsys.readouterr()
    assert result is True
    # Default title 'Episode 8' should appear in filename
    assert 'Episode 08 - Episode 8.mp4' in captured.out 
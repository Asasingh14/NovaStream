import os
import src.downloader as dlmod
from src.downloader import run_download

class DummyPool:
    def __init__(self, workers):
        self.workers = workers
    def imap_unordered(self, func, args):
        # Call the function for each argument
        for arg in args:
            func(arg)
            yield None
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class DummyTk:
    def __init__(self):
        pass
    def withdraw(self):
        pass
    def destroy(self):
        pass


def test_run_download_static_url(monkeypatch, tmp_path, capsys):
    calls = []
    # Stub find_episode_links to return empty (static URL case)
    monkeypatch.setattr(dlmod, 'find_episode_links', lambda url: [])
    # Stub banner to record call
    monkeypatch.setattr(dlmod, 'banner', lambda: calls.append('banner'))
    # Stub download_episode to record call args
    monkeypatch.setattr(dlmod, 'download_episode', lambda args: calls.append(args))
    # Use DummyPool instead of real Pool
    monkeypatch.setattr(dlmod.mp, 'Pool', DummyPool)
    # Stub tkinter.Tk to avoid real GUI
    monkeypatch.setattr(dlmod.tk, 'Tk', DummyTk)
    # Stub simpledialog.askstring to return None so that it skips
    monkeypatch.setattr(dlmod.simpledialog, 'askstring', lambda title, text, initialvalue=None: None)
    # Stub messagebox calls
    monkeypatch.setattr(dlmod.messagebox, 'showerror', lambda title, text: calls.append('error:'+text))
    monkeypatch.setattr(dlmod.messagebox, 'showinfo', lambda title, text: calls.append('info:'+text))
    # Run download on static episode URL
    url = 'http://example.com/show/episode-3'
    run_download(url, 'MyShow', str(tmp_path), False, '', 2)
    # Banner should have been called
    assert 'banner' in calls
    # download_episode should have been called once with expected args
    drama_dir = os.path.join(str(tmp_path), 'MyShow')
    assert ('MyShow', 3, url, drama_dir) in calls
    # showinfo should have been called
    assert any(isinstance(call, str) and call.startswith('info:') for call in calls) 
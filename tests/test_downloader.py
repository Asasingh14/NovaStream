import os
import pytest
from src.downloader import download_episode
import src.downloader as dlmod

class DummyRes:
    def __init__(self, code):
        self.returncode = code

class DummyPopen:
    def __init__(self, cmd, stdout, stderr, preexec_fn=None):
        pass
    def wait(self):
        return 0

def test_download_episode_no_manifest(tmp_path, capsys, monkeypatch):
    # No manifests => error message
    monkeypatch.setattr(dlmod, 'get_manifest_urls', lambda url: set())
    args = ('Show', 1, 'http://x', str(tmp_path))
    download_episode(args)
    captured = capsys.readouterr()
    assert '[#1]' in captured.out and 'No manifest found' in captured.out


def test_download_episode_skip_existing(tmp_path, capsys, monkeypatch):
    # Manifest present but file exists => skip
    monkeypatch.setattr(dlmod, 'get_manifest_urls', lambda url: {'http://x/media.m3u8'})
    # Force raw_title fallback
    monkeypatch.setattr(dlmod.requests, 'get', lambda url: (_ for _ in ()).throw(Exception()))
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
    monkeypatch.setattr(dlmod.requests, 'get', lambda url: (_ for _ in ()).throw(Exception()))
    # Stub subprocess.Popen to succeed
    monkeypatch.setattr(dlmod.subprocess, 'Popen', DummyPopen)
    args = ('Show', 2, 'http://x', str(tmp_path))
    download_episode(args)
    captured = capsys.readouterr()
    assert 'Download complete' in captured.out 
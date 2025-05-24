import pytest
from src.utils import banner, text2art
from colorama import Fore

def test_banner(monkeypatch, capsys):
    # Monkeypatch text2art to return a known banner
    monkeypatch.setattr('src.utils.text2art', lambda title: 'MOCK_ART')
    banner()
    captured = capsys.readouterr()
    # The output should include the mocked art and start with cyan color code
    assert 'MOCK_ART' in captured.out
    assert captured.out.startswith(Fore.CYAN) 
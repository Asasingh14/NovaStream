import pytest
from src.driver import get_driver

class DummyOptions:
    def __init__(self):
        self.args = []
    def add_argument(self, arg):
        self.args.append(arg)

class DummyService:
    def __init__(self, path):
        self.path = path

class DummyWebdriver:
    def __init__(self, service=None, options=None):
        self.service = service
        self.options = options

    def quit(self):
        pass

@pytest.fixture(autouse=True)
def setup_monkey(monkeypatch):
    # Stub the ChromeDriverManager.install to return a fake path
    monkeypatch.setattr('webdriver_manager.chrome.ChromeDriverManager.install', lambda self: '/fake/path', raising=True)
    # Replace Options and Service with dummy classes
    monkeypatch.setattr('selenium.webdriver.chrome.options.Options', DummyOptions, raising=True)
    monkeypatch.setattr('selenium.webdriver.chrome.service.Service', DummyService, raising=True)
    # Stub webdriver.Chrome to use DummyWebdriver
    monkeypatch.setattr('seleniumwire.webdriver.Chrome', lambda *args, **kwargs: DummyWebdriver(kwargs.get('service'), kwargs.get('options')), raising=True)


def test_get_driver_returns_correct_instance():
    driver = get_driver()
    assert isinstance(driver, DummyWebdriver)


def test_get_driver_configures_headless_and_gpu():
    driver = get_driver()
    # Options were provided to DummyWebdriver
    assert '--headless' in driver.options.args
    assert '--disable-gpu' in driver.options.args 
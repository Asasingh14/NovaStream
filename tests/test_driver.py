import pytest
import src.driver as driver_mod
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
    monkeypatch.setattr(driver_mod.ChromeDriverManager, 'install', lambda self: '/fake/path')
    # Replace Options and Service with dummy classes
    monkeypatch.setattr(driver_mod, 'Options', DummyOptions)
    monkeypatch.setattr(driver_mod, 'Service', DummyService)
    # Stub webdriver.Chrome to use DummyWebdriver
    monkeypatch.setattr(driver_mod.webdriver, 'Chrome', lambda service, options: DummyWebdriver(service, options))


def test_get_driver_returns_correct_instance():
    driver = get_driver()
    assert isinstance(driver, DummyWebdriver)


def test_get_driver_configures_headless_and_gpu():
    driver = get_driver()
    # Options were provided to DummyWebdriver
    assert '--headless' in driver.options.args
    assert '--disable-gpu' in driver.options.args 
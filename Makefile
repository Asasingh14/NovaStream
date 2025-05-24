.PHONY: test coverage

test:
	pytest

coverage:
	coverage run -m pytest
	coverage xml -o coverage.xml
	coverage html

clean:
	rm -rf .pytest_cache htmlcov coverage.xml 
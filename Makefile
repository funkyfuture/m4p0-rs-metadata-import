.DEFAULT_GOAL := tests

define PRINT_HELP_PYSCRIPT
import re, sys
for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT


.PHONY: black
black: ## normalize Python code
	black rs_import tests setup.py

.PHONY: flake8
flake8: ## code linting with flake8
	flake8 --max-line-length=89 rs_import tests setup.py

.PHONY: help
help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

.PHONY: mypy
mypy: ## run static type checks with mypy
	mypy rs_import

.PHONY: pytest
pytest: ## run the test suite
	python -m pytest --cov-config .coveragerc --cov=rs_import tests

.PHONY: tests ## run all tests on normalized code
tests: black flake8 mypy pytest

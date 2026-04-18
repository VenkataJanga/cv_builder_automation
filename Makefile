PYTHON ?= python
PIP ?= $(PYTHON) -m pip
PYTEST ?= $(PYTHON) -m pytest

export PYTHONPATH := .

.PHONY: help install test test-regression test-api-logging ci

help:
	@echo "Available targets:"
	@echo "  install             Install project dependencies in editable mode"
	@echo "  test                Run full test suite"
	@echo "  test-regression     Run workflow name-persistence regression tests"
	@echo "  test-api-logging    Run transaction event logging API tests"
	@echo "  ci                  Run core regression checks used in CI"

install:
	$(PIP) install -e .

test:
	$(PYTEST) -q tests

test-regression:
	$(PYTEST) -q tests/test_workflow_name_persistence_regression.py

test-api-logging:
	$(PYTEST) -q tests/test_transaction_event_logging_api.py

ci: test-regression test-api-logging

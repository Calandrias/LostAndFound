# Simple Makefile for Lost & Found QR Platform

PYTHON := poetry run python3
SHARED_SRC := $(PWD)/runtime/shared/src
export PYTHONPATH := $(SHARED_SRC):$(PYTHONPATH)



.PHONY: all lint test clean generate-schemas generate-api generate-lambdas generate help

all: help

## Show this help.
help:
	@awk ' \
		/^[a-zA-Z0-9][^:]*:/ { \
			if (prev && match(prev, /^##/)) { \
				sub(/^## ?/, "", prev); \
				printf "  \033[36m%-20s\033[0m %s\n", $$1, prev \
			} \
		} \
		{ prev = $$0 }' $(MAKEFILE_LIST)

## Lint Python source code with pylint
lint:
	$(PYTHON) -m pylint $(shell git ls-files '*.py')

## Run unit tests with pytest
test:
	$(PYTHON) -m pytest

## Remove Python cache & test files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +

## Generate OpenAPI schemas from Pydantic models
generate-schemas:
	$(PYTHON) api/devtools/s1_generate_schemas.py

## Parse and validate OpenAPI spec
generate-api:
	$(PYTHON) api/devtools/s2_generate_api.py

## Generate lambda runtime and resources
generate-lambdas:
	$(PYTHON) api/devtools/s3_generate_lambdas.py

## Run all generate steps
generate: generate-schemas generate-api generate-lambdas

## Install dependencys
install: 
	poetry install

## Make Layer from runtime/shared "editable"
editable:
	poetry run pip install -e runtime/shared


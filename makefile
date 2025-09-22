# Simple Makefile for Lost & Found QR Platform

# Python interpreter
PYTHON := python3

# Source directory
SRC_DIR := src

.PHONY: lint test all clean

# Default target
all: lint test

# Run pylint
lint:
	$(PYTHON) -m pylint $(shell git ls-files '*.py')
# Run pytest  
test:
	$(PYTHON) -m pytest

# Clean up cache files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +

# Generate OpenAPI schemas from Pydantic models
.PHONY: generate-schemas

generate-schemas:
	python api/devtools/generate_schemas.py

# Parse and validate OpenAPI spec
.PHONY: parse-api

parse-api:
	python api/devtools/api_parser.py

# Run both schema generation and parsing in sequence
.PHONY: spec

spec: generate-schemas parse-api

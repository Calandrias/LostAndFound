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

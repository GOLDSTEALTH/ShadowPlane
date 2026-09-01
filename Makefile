.PHONY: help build run test

VERSION := $(shell cat VERSION)
IMAGE_NAME := shadowplane

help:
	@echo "ShadowPlane Gatekeeper Makefile"
	@echo ""
	@echo "Commands:"
	@echo "  make build    Build the Docker image using the current VERSION"
	@echo "  make run      Run the Docker container locally (bind-mounts docker.sock)"
	@echo "  make test     Run the CLI locally to verify syntax and help output"

build:
	@echo "Building $(IMAGE_NAME):$(VERSION)..."
	docker build $(ARGS) --build-arg VERSION=$(VERSION) -t $(IMAGE_NAME):$(VERSION) -t $(IMAGE_NAME):latest .
run:
	@echo "Running $(IMAGE_NAME):$(VERSION) locally..."
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock $(IMAGE_NAME):$(VERSION) --target-dir ./demo-infra

test:
	python cli.py --help
	python cli.py --version

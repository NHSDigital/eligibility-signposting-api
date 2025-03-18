SHELL := /bin/bash
dirname := $(notdir $(patsubst %/,%,$(CURDIR)))
project_name = eligibility-signposting-api

list:
	@grep '^[^#[:space:]].*:' Makefile

build:
	docker-compose -f docker-compose.yaml build

up: build
	docker-compose -f docker-compose.yaml up -d

down:
	docker-compose -f docker-compose.yaml down

clean:
	rm -rf ./node_modules

install:
	npm install --dev

update:
	npm update

spec:
	make -C .. publish

test:
	UPSTREAM_HOST=test poetry run pytest

.PHONY: build run spec test

.PHONY: help all default clean clean-build clean-pyc clean-test install lint security-check tests test build

help:
	@echo "clean - remove all build, test, coverage and Python artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "clean-test - remove test and coverage artifacts"
	@echo "lint - check style"
	@echo "tests - run all the test files"
	@echo "test - run an indidivual test file"
	@echo "install - install all the packages"
	@echo "build - package"

clean-build:
	rm -fr dist/

build: clean
	mkdir ./dist
	cp ./spark/utils/spark_session.py ./requirements.txt ./dist
	zip -x ./spark/utils/spark_session.py ./requirements.txt -r ./dist/jobs.zip ./spark
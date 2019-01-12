init:
	pip install -r requirements.txt

test:
	py.test-3 tests

.PHONY: init test

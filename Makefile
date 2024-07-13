.PHONY: test

test:
    # TEST_PATTERN="test_aggregators" make test
	# PYTHONPATH=. pipenv run pytest -vrP $(if $(TEST_PATTERN),-k "$(TEST_PATTERN)",)
	PYTHONPATH=. pipenv run pytest -vrP $(if $(TEST_PATTERN),-k "$(TEST_PATTERN)",)
.PHONY: test bot participant fly-secrets

fly-secrets:
	cat .env | tr '\n' ' ' | xargs flyctl secrets set

test:
    # TEST_PATTERN="test_aggregators" make test
	# PYTHONPATH=. pipenv run pytest -vrP $(if $(TEST_PATTERN),-k "$(TEST_PATTERN)",)
	PYTHONPATH=. pipenv run pytest -vrP $(if $(TEST_PATTERN),-k "$(TEST_PATTERN)",) tests/

bot:
	pipenv run python ./bot.py

participant:
	pipenv run python ./participant.py

deploy-bot:
	pipenv run python ./bot_runner.py --deploy-bot
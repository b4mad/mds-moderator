.PHONY: test bot participant deploy-bot fly-secrets fly-launch fly-build fly-deploy-bot

test:
    # TEST_PATTERN="test_aggregators" make test
	# PYTHONPATH=. pipenv run pytest -vrP $(if $(TEST_PATTERN),-k "$(TEST_PATTERN)",)
	PYTHONPATH=. pipenv run pytest -vrP $(if $(TEST_PATTERN),-k "$(TEST_PATTERN)",) tests/

bot:
	pipenv run python ./bot.py

participant:
	pipenv run python ./participant.py

docker-build-linux:
	docker build --tag=durandom/mds-moderator --platform linux/amd64  .

docker-run-bash:
	docker run -it --rm durandom/mds-moderator bash

fly-launch:
	flyctl launch

fly-secrets:
	cat .env | tr '\n' ' ' | xargs flyctl secrets set

fly-build:
	flyctl deploy --build-only

fly-deploy-bot:
	pipenv run python ./bot_runner.py --deploy-bot


# Load environment variables from .env file
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

.PHONY: test bot participant deploy-bot fly-secrets fly-launch fly-build fly-deploy-bot docker-build-linux docker-run-bash docker-run-bot bot-with-prompt

test:
    # TEST_PATTERN="test_aggregators" make test
	# PYTHONPATH=. pipenv run pytest -vrP $(if $(TEST_PATTERN),-k "$(TEST_PATTERN)",)
	PYTHONPATH=. pipenv run pytest -vrP $(if $(TEST_PATTERN),-k "$(TEST_PATTERN)",) tests/

bot:
	pipenv run python ./bot.py

bot-runner:
	pipenv run env RUN_AS_PROCESS=true  python ./bot_runner.py

participant:
	pipenv run python ./participant.py

docker-build:
	docker build --tag=durandom/mds-moderator .

docker-build-linux:
	docker build --tag=durandom/mds-moderator --platform linux/amd64  .

docker-run-bash:
	docker run -it --rm durandom/mds-moderator bash

docker-run-bot:
	docker run -p 7860:7860 --env-file .env durandom/mds-moderator


# creates the new fly app
fly-launch:
	flyctl launch

fly-secrets:
	cat .env | tr '\n' ' ' | xargs flyctl secrets set

fly-build:
	flyctl deploy --build-only

fly-deploy:
	flyctl deploy

fly-deploy-bot:
	pipenv run python ./bot_runner.py --deploy-bot

# starts a bot with a prompt on fly.io
bot-with-prompt:
	curl --verbose --location --request POST "$${DEPLOYMENT_URL}/start_bot" \
		--header 'Content-Type: application/json' \
		--trace-ascii /dev/stdout \
		--data @start_bot.json

bot-with-prompt-local:
	curl --verbose --location --request POST "http://localhost:7860/start_bot" \
		--header 'Content-Type: application/json' \
		--trace-ascii /dev/stdout \
		--data @start_bot.json

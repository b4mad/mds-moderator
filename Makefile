# Load environment variables from .env file
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# use `docker` as a CONTAINER_ENGINE or `podman` as a default to build container images
ifeq ($(shell which docker),)
	CONTAINER_ENGINE := $(shell which podman)
else
	CONTAINER_ENGINE := $(shell which docker)
endif

.PHONY: test
test:
    # TEST_PATTERN="test_aggregators" make test
	# PYTHONPATH=. pipenv run pytest -vrP $(if $(TEST_PATTERN),-k "$(TEST_PATTERN)",)
	PYTHONPATH=. pipenv run pytest -vrP $(if $(TEST_PATTERN),-k "$(TEST_PATTERN)",) tests/

.PHONY: bot
bot: bot.py
	pipenv run ./bot.py

bot-runner:
	pipenv run env RUN_AS_PROCESS=true  python ./bot_runner.py

.PHONY: participant
participant:
	pipenv run python ./participant.py

.PHONY: container-build container-build-linux container-run-bash container-run-bot
container-build:
	$(CONTAINER_ENGINE) build --tag=durandom/mds-moderator .

container-build-linux:
	$(CONTAINER_ENGINE) build --tag=durandom/mds-moderator --platform linux/amd64  .

container-run-bash:
	$(CONTAINER_ENGINE) run -it --rm -v $(PWD):/app --platform linux/amd64 python:3.12.3-bookworm bash

container-run-bot:
	$(CONTAINER_ENGINE) run -p 7860:7860 --env-file .env durandom/mds-moderator


# creates the new fly app
.PHONY: fly-secrets fly-launch fly-build fly-deploy fly-deploy-bot
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
.PHONY: bot-with-prompt bot-with-prompt-local
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

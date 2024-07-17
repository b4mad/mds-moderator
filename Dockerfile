FROM python:3.12.3-bookworm AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

ENV PIPENV_VENV_IN_PROJECT=1 \
    PIPENV_CUSTOM_VENV_NAME=.venv
RUN pip install pipenv
COPY Pipfile Pipfile.lock ./
RUN pipenv install

FROM python:3.12.3-slim-bookworm
# Open port 7860 for http service
ENV FAST_API_PORT=7860
EXPOSE 7860

WORKDIR /app
COPY --from=builder /app/.venv .venv/
COPY *.py .
COPY assets assets
# Install dependencies
RUN apt-get update && \
    apt-get install -y libgomp1 && \
    rm -rf /var/lib/apt/lists/*

# # Install CPU-only version of PyTorch
RUN . .venv/bin/activate && pip install torch==2.3.1+cpu torchaudio==2.3.1+cpu -f https://download.pytorch.org/whl/torch_stable.html

# Install models
RUN /app/.venv/bin/python3 install_deps.py
# And start the FastAPI server
CMD /app/.venv/bin/python3 bot_runner.py --port ${FAST_API_PORT}
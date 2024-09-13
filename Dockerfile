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
ENV NODE_MAJOR=20
EXPOSE 7860

WORKDIR /app
# Install dependencies
RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    build-essential \
    google-perftools \
    ca-certificates curl gnupg \
    libgomp1 && \
    rm -rf /var/lib/apt/lists/*


COPY --from=builder /app/.venv .venv/

# Install Node.js
RUN mkdir -p /etc/apt/keyrings
RUN curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
RUN echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_${NODE_MAJOR}.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list > /dev/null
RUN apt-get update && apt-get install nodejs -y

# Install CPU-only version of PyTorch based on architecture
RUN if [ "$(uname -m)" = "x86_64" ]; then \
        .venv/bin/pip install torch==2.3.1+cpu torchaudio==2.3.1+cpu -f https://download.pytorch.org/whl/torch_stable.html; \
    elif [ "$(uname -m)" = "aarch64" ]; then \
        .venv/bin/pip install torch==2.3.1 torchaudio==2.3.1; \
    else \
        echo "Unsupported architecture: $(uname -m)"; \
        exit 1; \
    fi

# Install models
COPY install_deps.py .
RUN /app/.venv/bin/python3 install_deps.py

# Set up a new user named "user" with user ID 1000
RUN useradd -m -u 1000 user

# Copy the rest of the app
COPY *.py .
COPY assets assets

# Set home to the user's home directory
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONPATH=$HOME/app \
    PYTHONUNBUFFERED=1

RUN mkdir /app/logs && chown user:user /app/logs

# Switch to the "user" user
USER user

# Copy frontend app and build
COPY --chown=user ./frontend/ frontend/
RUN cd frontend && npm install && npm run build

# create an /app/logs directory

# And start the FastAPI server
CMD /app/.venv/bin/python3 bot_runner.py --port ${FAST_API_PORT}

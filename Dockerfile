FROM python:3.12-slim

RUN useradd -m -u 1000 agent \
    && mkdir /workspace \
    && chown agent:agent /workspace

RUN pip install --no-cache-dir pytest

USER agent
WORKDIR /workspace
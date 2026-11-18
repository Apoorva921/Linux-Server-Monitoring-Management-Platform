FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /agent

RUN groupadd --system sentinelops && useradd --system --gid sentinelops --no-create-home sentinelops

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .
RUN chown -R sentinelops:sentinelops /agent

USER sentinelops

CMD ["python", "agent.py"]


#builder
FROM python:3.11-slim AS builder

LABEL org.opencontainers.image.title="Kafka Producer" \
      org.opencontainers.image.description="Kafka producer" \
      org.opencontainers.image.version="0.0.1" \
      org.opencontainers.image.authors="Kevin Odhiambo"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    && wget -O /app/google-chrome-stable_current_amd64.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get purge -y --auto-remove wget \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

#runner
FROM python:3.11-slim AS runner

WORKDIR /app

COPY --from=builder /app/google-chrome-stable_current_amd64.deb .
RUN apt-get update && apt-get install -y --no-install-recommends \
    ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

#copy the pre-installed Python packages from builder stage
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUSERBASE=/root/.local

COPY wait-for-it.sh firms.json extraction.py ./
RUN chmod +x wait-for-it.sh

CMD ["sh", "-c", "./wait-for-it.sh -s -t 30 $KAFKA_SERVER -- python -u extraction.py"]
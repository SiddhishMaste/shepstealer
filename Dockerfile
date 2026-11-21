FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential cmake \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
    && cmake --build build -j2 \
    && pip install --no-cache-dir -r server/requirements.txt

ENV SHEEPSTEALER_BIN=/app/build/sheepstealer
ENV PORT=10000
EXPOSE 10000

RUN useradd --create-home runner
USER runner

CMD gunicorn --chdir server --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 90 app:app

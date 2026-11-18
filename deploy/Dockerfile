# monev-bot: bot Telegram pribadi (pengingat & rekap Monev, tanpa AI). Hanya membaca Monev.
# Data (sesi Chrome, config, state) di volume /data.
FROM python:3.12-slim

# Google Chrome resmi (amd64). Dipakai Playwright lewat channel="chrome".
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates wget \
 && wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
 && apt-get install -y --no-install-recommends /tmp/chrome.deb \
 && rm -rf /var/lib/apt/lists/* /tmp/chrome.deb

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY monev ./monev
# Versi dependency mengikuti uv.lock.
RUN pip install --no-cache-dir uv \
 && uv export --frozen --no-hashes --no-emit-project -o /tmp/req.txt \
 && pip install --no-cache-dir -r /tmp/req.txt \
 && pip install --no-cache-dir --no-deps . \
 && pip uninstall -y uv && rm /tmp/req.txt

RUN useradd -m -u 1000 monev && mkdir -p /data && chown monev:monev /data
USER monev

ENV MONEV_DATA_DIR=/data \
    MONEV_CONFIG=/data/config.toml \
    MONEV_CHROME_ARGS="--no-sandbox --disable-dev-shm-usage" \
    PYTHONUNBUFFERED=1
VOLUME /data
CMD ["monev", "bot"]

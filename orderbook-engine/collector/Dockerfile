FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY binance_depth_collector.py healthcheck.py .

ENV DATA_DIR=/data/binance
VOLUME ["/data"]
CMD ["python", "-u", "binance_depth_collector.py"]

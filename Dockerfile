FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    jq \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    libappindicator3-1 \
    libnss3 \
    libxss1 \
    libasound2 \
    libgbm-dev \
    ca-certificates \
    fonts-liberation \
    libvulkan1 \
    xdg-utils && \
    rm -rf /var/lib/apt/lists/*

RUN LATEST_VERSION=$(curl -s https://googlechromelabs.github.io/chrome-for-testing/latest-patch-versions-per-build.json | jq -r '.builds["stable"]') && \
    mkdir -p /opt/chrome && \
    wget https://storage.googleapis.com/chrome-for-testing-public/$LATEST_VERSION/linux64/chrome-linux64.zip -O /tmp/chrome-linux64.zip && \
    wget https://storage.googleapis.com/chrome-for-testing-public/$LATEST_VERSION/linux64/chromedriver-linux64.zip -O /tmp/chromedriver-linux64.zip && \
    unzip /tmp/chrome-linux64.zip -d /opt/chrome && \
    unzip /tmp/chromedriver-linux64.zip -d /usr/local/bin/ && \
    rm /tmp/chrome-linux64.zip /tmp/chromedriver-linux64.zip && \
    mv /opt/chrome/chrome-linux64/chrome /usr/bin/google-chrome && \
    mv /opt/chrome/chrome-linux64/chrome-sandbox /usr/bin/chrome-sandbox && \
    chmod +x /usr/bin/google-chrome /usr/bin/chrome-sandbox /usr/local/bin/chromedriver

ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver

WORKDIR /usr/src/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8087

CMD ["python", "bot.py"]

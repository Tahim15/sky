FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
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

RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt install -y ./google-chrome-stable_current_amd64.deb && \
    rm google-chrome-stable_current_amd64.deb

RUN CHROME_VERSION=112.0.5615.138 && \
    echo "Using Chrome Version: $CHROME_VERSION" && \
    CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION") && \
    echo "Detected Chromedriver Version: $CHROMEDRIVER_VERSION" && \
    if [ -z "$CHROMEDRIVER_VERSION" ]; then \
        echo "Error: Chromedriver version for Chrome $CHROME_VERSION not found"; exit 1; \
    fi && \
    echo "Downloading Chromedriver version $CHROMEDRIVER_VERSION..." && \
    wget --retry-connrefused --waitretry=1 --timeout=15 --tries=3 -q "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" -O /tmp/chromedriver.zip && \
    echo "Unzipping Chromedriver..." && \
    unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
    rm /tmp/chromedriver.zip && \
    chmod +x /usr/local/bin/chromedriver

ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver

WORKDIR /usr/src/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8087

CMD ["python", "bot.py"]

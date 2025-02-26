# Use a slim Python base image
FROM python:3.10-slim

# Install dependencies
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

# Install the specific version of Google Chrome (133.0.6943.132)
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_133.0.6943.132-1_amd64.deb && \
    apt install -y ./google-chrome-stable_133.0.6943.132-1_amd64.deb && \
    rm google-chrome-stable_133.0.6943.132-1_amd64.deb

# Install the matching Chromedriver version (133.0.2)
RUN CHROMEDRIVER_VERSION="133.0.2" && \
    echo "Detected Chromedriver Version: $CHROMEDRIVER_VERSION" && \
    wget --retry-connrefused --waitretry=1 --timeout=15 --tries=3 -q "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" -O /tmp/chromedriver.zip && \
    unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
    rm /tmp/chromedriver.zip && \
    chmod +x /usr/local/bin/chromedriver

# Set environment variables
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver

WORKDIR /usr/src/app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your app
COPY . .

EXPOSE 8087

CMD ["python", "bot.py"]

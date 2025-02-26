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

# Create a directory for Chrome and install Google Chrome there
RUN echo "Starting download of Google Chrome..." && \
    mkdir -p /opt/chrome && \
    wget https://storage.googleapis.com/chrome-for-testing-public/133.0.6943.141/linux64/chrome-linux64.zip -O /tmp/chrome-linux64.zip && \
    echo "Unzipping Google Chrome..." && \
    unzip /tmp/chrome-linux64.zip -d /opt/chrome && \
    rm /tmp/chrome-linux64.zip && \
    echo "List contents of /opt/chrome/:" && \
    ls -la /opt/chrome && \
    echo "Checking if google-chrome exists:" && \
    find /opt/chrome -name "google-chrome" && \
    echo "Checking if chrome-sandbox exists:" && \
    find /opt/chrome -name "chrome-sandbox" && \
    echo "Attempting to move google-chrome to /usr/bin/google-chrome..." && \
    mv /opt/chrome/google-chrome /usr/bin/google-chrome && \
    echo "Attempting to move chrome-sandbox to /usr/bin/chrome-sandbox..." && \
    mv /opt/chrome/chrome-sandbox /usr/bin/chrome-sandbox && \
    echo "Changing permissions for google-chrome and chrome-sandbox..." && \
    chmod +x /usr/bin/google-chrome /usr/bin/chrome-sandbox && \
    echo "Google Chrome installation complete."

# Install Chromedriver
RUN echo "Downloading Chromedriver..." && \
    wget https://storage.googleapis.com/chrome-for-testing-public/133.0.6943.141/linux64/chromedriver-linux64.zip -O /tmp/chromedriver-linux64.zip && \
    unzip /tmp/chromedriver-linux64.zip -d /usr/local/bin/ && \
    rm /tmp/chromedriver-linux64.zip && \
    chmod +x /usr/local/bin/chromedriver && \
    echo "Chromedriver installation complete."

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

# Set the working directory where the bot resides and run it
WORKDIR /usr/src/app
CMD ["python", "bot.py"]

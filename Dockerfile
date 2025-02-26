FROM python:3.10-slim

# Install required dependencies
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

# Create directories for Chrome and Chromedriver
RUN mkdir -p /opt/chrome /opt/chromedriver

# Fetch the latest stable version of Chrome for Testing
RUN LATEST_VERSION=$(curl -s https://googlechromelabs.github.io/chrome-for-testing/latest-patch-versions-per-build.json | jq -r '.builds.stable') && \
    echo "Latest Chrome Version: $LATEST_VERSION" && \
    
    # Download Chrome and Chromedriver
    wget https://storage.googleapis.com/chrome-for-testing-public/$LATEST_VERSION/linux64/chrome-linux64.zip -O /tmp/chrome-linux64.zip && \
    wget https://storage.googleapis.com/chrome-for-testing-public/$LATEST_VERSION/linux64/chromedriver-linux64.zip -O /tmp/chromedriver-linux64.zip && \

    # Unzip the downloaded files
    unzip /tmp/chrome-linux64.zip -d /opt/chrome/ && \
    unzip /tmp/chromedriver-linux64.zip -d /opt/chromedriver/ && \

    # Remove zip files
    rm /tmp/chrome-linux64.zip /tmp/chromedriver-linux64.zip && \

    # Move the binaries to the appropriate locations
    mv /opt/chrome/chrome-linux64/chrome /usr/bin/google-chrome && \
    mv /opt/chrome/chrome-linux64/chrome-sandbox /usr/bin/chrome-sandbox && \
    mv /opt/chromedriver/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \

    # Set the correct permissions
    chmod +x /usr/bin/google-chrome /usr/bin/chrome-sandbox /usr/local/bin/chromedriver

# Set environment variables
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver

# Set the working directory
WORKDIR /usr/src/app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the application port
EXPOSE 8087

# Run the application
CMD ["python", "bot.py"]

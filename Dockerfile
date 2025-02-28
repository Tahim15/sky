FROM python:3.10-slim

# Install required dependencies
RUN apt-get update && apt-get install -y git
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

# Set working directory
WORKDIR /opt

# Define Chrome version (HARD-CODED to avoid dynamic failures)
ENV CHROME_VERSION=133.0.6943.141

# Download and install Chrome & Chromedriver (matching versions)
RUN echo "Installing Chrome version $CHROME_VERSION..." && \
    wget -O /tmp/chrome-linux64.zip "https://storage.googleapis.com/chrome-for-testing-public/$CHROME_VERSION/linux64/chrome-linux64.zip" && \
    wget -O /tmp/chromedriver-linux64.zip "https://storage.googleapis.com/chrome-for-testing-public/$CHROME_VERSION/linux64/chromedriver-linux64.zip" && \

    # Unzip Chrome & Chromedriver
    unzip /tmp/chrome-linux64.zip -d /opt/chrome/ && \
    unzip /tmp/chromedriver-linux64.zip -d /opt/chromedriver/ && \

    # Remove ZIP files
    rm /tmp/chrome-linux64.zip /tmp/chromedriver-linux64.zip && \

    # Move binaries to correct locations
    mv /opt/chrome/chrome-linux64/chrome /usr/bin/google-chrome && \
    mv /opt/chromedriver/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \

    # Set correct permissions
    chmod +x /usr/bin/google-chrome /usr/local/bin/chromedriver && \

    # Verify installation
    google-chrome --version && \
    chromedriver --version

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

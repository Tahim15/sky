FROM python:3.10-slim

# Install necessary dependencies
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

# Download and install the specific version of Google Chrome (133.0.6943.141)
RUN wget https://storage.googleapis.com/chrome-for-testing-public/133.0.6943.141/linux64/chrome-linux64.zip -O /tmp/chrome-linux64.zip && \
    unzip /tmp/chrome-linux64.zip -d /opt/ && \
    rm /tmp/chrome-linux64.zip && \
    mv /opt/google-chrome-stable*/google-chrome /usr/bin/google-chrome && \
    mv /opt/google-chrome-stable*/chrome-sandbox /usr/bin/chrome-sandbox && \
    chmod +x /usr/bin/google-chrome /usr/bin/chrome-sandbox

# Download and install the specific version of Chromedriver (133.0.6943.141)
RUN wget https://storage.googleapis.com/chrome-for-testing-public/133.0.6943.141/linux64/chromedriver-linux64.zip -O /tmp/chromedriver-linux64.zip && \
    unzip /tmp/chromedriver-linux64.zip -d /usr/local/bin/ && \
    rm /tmp/chromedriver-linux64.zip && \
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

# Expose port
EXPOSE 8087

# Set the default command to run your bot
CMD ["python", "bot.py"]

FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    wget unzip curl xvfb \
    libxi6 libgconf-2-4 libappindicator3-1 \
    libnss3 libxss1 libasound2 libgbm-dev \
    chromium chromium-driver && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

WORKDIR /usr/src/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8087

CMD ["python", "bot.py"]

FROM python:3.12-alpine

# Chromium + dependances pour Puppeteer
RUN apk add --no-cache \
    chromium \
    nss \
    freetype \
    harfbuzz \
    ttf-freefont \
    ca-certificates \
    nodejs \
    npm \
    curl \
    bash \
    && rm -rf /var/cache/apk/*

# Variables pour Puppeteer (utiliser le Chromium systeme)
ENV CHROME_PATH=/usr/bin/chromium
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

WORKDIR /app

# Installer les deps Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installer les deps Node (puppeteer-core)
COPY package.json .
RUN npm install --omit=dev

# Copier le code
COPY . .

# Dossier de stockage
RUN mkdir -p /app/storage/images

EXPOSE 8765

CMD ["python", "bridge_server.py"]
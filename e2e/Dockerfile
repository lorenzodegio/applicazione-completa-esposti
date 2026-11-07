# Browser vero (Chromium) con la stessa versione di @playwright/test (fissata in package.json).
FROM mcr.microsoft.com/playwright:v1.63.0-noble
ENV NPM_CONFIG_UPDATE_NOTIFIER=false NPM_CONFIG_FUND=false NPM_CONFIG_AUDIT=false CI=1
WORKDIR /e2e
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
CMD ["npx", "playwright", "test"]

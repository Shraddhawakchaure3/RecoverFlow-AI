# ─── Frontend Dockerfile ──────────────────────────────────────────────────────
# Use Node 20 LTS — compatible with Vite 8 + React 19
FROM node:20-slim

WORKDIR /app

# Copy package files first for layer caching
COPY package.json package-lock.json ./

# Install all deps (including devDeps needed for Vite build/dev)
RUN npm ci

# Copy application source
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Run Vite dev server on 0.0.0.0 so Docker can forward the port
CMD ["npm", "run", "dev"]

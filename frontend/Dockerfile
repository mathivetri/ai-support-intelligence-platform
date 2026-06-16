# syntax=docker/dockerfile:1
#
# Frontend image — multi-stage: build the Vite app, serve the static
# bundle with nginx (which also reverse-proxies /api to the backend).
#
#     docker build -t support-frontend ./frontend

# ── Stage 1: build ────────────────────────────────────────────────────────
FROM node:22-alpine AS build

WORKDIR /app

# Install deps first (cached unless the lockfile changes).
COPY package.json package-lock.json ./
RUN npm ci

# Build the production bundle into /app/dist.
COPY . .
RUN npm run build

# ── Stage 2: serve ────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

# SPA routing + API proxy config.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Static assets from the build stage.
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

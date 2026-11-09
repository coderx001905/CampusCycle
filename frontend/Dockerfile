# Stage 1: Build production frontend assets
FROM node:20-alpine AS build

WORKDIR /app

# Copy dependency manifests first for optimal layer caching
COPY package.json package-lock.json ./
RUN npm ci

# Copy application source and build production bundle
COPY . .
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# Stage 2: Production web server serving static assets and proxying API
FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1/healthz > /dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]

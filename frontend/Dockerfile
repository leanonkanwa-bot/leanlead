# syntax=docker/dockerfile:1.7
# ── Build: compile React app ──────────────────────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci --prefer-offline

COPY . .
RUN npm run build

# ── Runtime: nginx serves static files + proxies /api ─────────────────────────
FROM nginx:1.27-alpine

# Remove default site, copy our config and built files
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

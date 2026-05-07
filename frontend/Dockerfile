# syntax=docker/dockerfile:1.7

FROM nginx:1.27-alpine

# Remove the default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy nginx config template (uses $BACKEND_URL placeholder)
COPY frontend/nginx.conf /etc/nginx/templates/default.conf.template

# Copy static frontend files
COPY frontend/index.html frontend/app.js frontend/style.css /app/frontend/

# Railway injects PORT=8080 by default; nginx listens on 8080 (see nginx.conf)
EXPOSE 8080

# envsubst injects $BACKEND_URL into the nginx config at container startup,
# then nginx runs in the foreground.
CMD ["/bin/sh", "-c", "envsubst '$BACKEND_URL' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]

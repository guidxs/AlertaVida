FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY index.html vite.config.js ./
COPY src ./src

RUN npm run build

FROM nginxinc/nginx-unprivileged:alpine AS runtime

# Apply Alpine security updates during the image build, then restore the
# unprivileged user configured by the nginx-unprivileged image.
USER root
RUN apk upgrade --no-cache
USER nginx

COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080

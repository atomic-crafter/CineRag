FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npx ng build --configuration production

FROM nginx:alpine
# Site password (basic auth, username "epf"); supplied at build time, never committed.
ARG WEB_PASSWORD
RUN test -n "$WEB_PASSWORD" || (echo "WEB_PASSWORD build arg is required" && exit 1)
RUN apk add --no-cache apache2-utils \
    && htpasswd -bc /etc/nginx/.htpasswd epf "$WEB_PASSWORD" \
    && apk del apache2-utils
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/FrontCineRag/browser /usr/share/nginx/html
EXPOSE 80

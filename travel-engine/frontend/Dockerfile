# Multi-stage: build Angular SPA, serve with nginx on port 8080 (Cloud Run PORT).
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx-cloudrun/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/travel-engine/browser /usr/share/nginx/html

EXPOSE 8080

# Cloud Run sends traffic to $PORT (default 8080). Nginx config listens on 8080.
CMD ["nginx", "-g", "daemon off;"]

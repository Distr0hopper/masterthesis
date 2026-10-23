# Frontend image - started by the root docker-compose.yml. Builds the SPA, then serves it
# with nginx, which also forwards /api/ to the backend (see nginx.conf)
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# read at build time: the browser reaches the API through nginx on the same origin
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM nginx:1.29-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80

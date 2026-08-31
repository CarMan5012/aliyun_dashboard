
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm config set registry https://registry.npmmirror.com/
RUN npm install
COPY . ./
RUN npm run build


FROM nginx:stable
COPY --from=builder /app/dist /usr/share/nginx/html
ENV NGINX_ENVSUBST_FILTER=SETTINGS_ADMIN_PASSWORD
COPY nginx.conf /etc/nginx/templates/default.conf.template
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

# 阶段 1: 构建 Vue + TS 项目
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm config set registry https://registry.npmmirror.com/
RUN npm install
COPY . ./
RUN npm run build

# 阶段 2: Nginx 稳定版托管 (兼容 CentOS 7 等各类 Linux 发行版内核)
FROM nginx:1.26
COPY --from=builder /app/dist /usr/share/nginx/html
ENV NGINX_ENVSUBST_FILTER=SETTINGS_ADMIN_PASSWORD
COPY nginx.conf /etc/nginx/templates/default.conf.template
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

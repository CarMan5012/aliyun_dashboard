# 阿里云资源看板 (Aliyun Resource Dashboard)

[![Docker Hub Frontend](https://img.shields.io/badge/docker--hub-frontend-blue?logo=docker)](https://hub.docker.com/r/carman5012/aliyun-dashboard-frontend)
[![Docker Hub Backend](https://img.shields.io/badge/docker--hub-backend-blue?logo=docker)](https://hub.docker.com/r/carman5012/aliyun-dashboard-backend)

本项目是一个高度自动化、现代美观的多账号云资源聚合监控与管理面板。支持通过 API 自动拉取和汇总展示阿里云的 **ECS 实例、弹性公网 IP (EIP)、域名资产** 以及 **SSL 证书**，内置内置定时调度、域名到期钉钉告警、多格式资产自定义导出以及敏感密钥端到端加密保护。

---

## 🎨 核心特性

1. **多账号聚合与隔离**：一站式接入与管理多个阿里云 AccessKey，自动拉取并合并展示资产，支持账号与资源类型的多维筛选。
2. **轻量化原生调度**：内置基于 APScheduler 的自动数据调度引擎，无需繁重消息队列中间件，支持为每个账号独立配置同步频率。
3. **域名到期智能告警**：
   * 支持到期天数动态阶梯预警，自动推送钉钉群消息。
   * 支持中国节假日/周末智能避峰，自动计算前序最近工作日进行告警推送。
   * 支持云解析 DNS 自动续费失败感知与失败重试调度。
4. **资产全量/自定义导出**：支持 CSV 与 JSON 格式导出，包含精准解析的公网 IP 列表（含 ECS 绑定 EIP 与固定公网 IP）、域名注册商信息及详细元数据。
5. **秒级实时同步计时器**：手动触发资产同步时，主内容区呈现精致毛玻璃 Banner，秒级实时展示同步耗时与执行进度。
6. **企业级安全保障**：
   * 阿里云 Secret Key 采用 Fernet (AES-256) 双向加密存储，接口层脱敏，前端永不接触明文密钥。
   * 管理设置页受口令保护，杜绝未授权修改。
7. **暗黑模式与现代 UI**：精美的深浅色主题切换，完美适配各种桌面分辨率。

---

## 🚀 快速开始与部署

### 1. 生成加密主密钥 (Master Key)
后端使用 AES-256 加密保存云账号密钥，部署前请先生成一个密钥：
```bash
python generate_key.py
# 或使用单行命令生成：
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

### 2. 生产环境部署 (推荐，使用 Docker Hub 镜像)

生产服务器**无需拉取项目源码**，只需准备配置文件即可启动：

1. **创建工作目录与配置文件**：
   ```bash
   mkdir -p /opt/aliyun-dashboard/data
   cd /opt/aliyun-dashboard
   ```

2. **配置环境变量 `.env`**：
   ```bash
   cat << 'EOF' > .env
   # 资产系统主密钥 (必填)
   ASSETVISTA_MASTER_KEY=你的Base64加密主密钥
   
   # 系统设置管理口令 (必填，用于保存告警配置等)
   SETTINGS_ADMIN_PASSWORD=你的管理员强密码
   EOF
   ```

3. **创建 `docker-compose.prod.yml`**：
   ```yaml
   services:
     backend:
       image: carman5012/aliyun-dashboard-backend:latest
       container_name: aliyun-dashboard-backend
       restart: always
       expose:
         - "8000"
       volumes:
         - ./data:/app/data
       environment:
         - DB_TYPE=sqlite
         - SQLITE_DB_PATH=/app/data/aliyun.db
         - "ASSETVISTA_MASTER_KEY=${ASSETVISTA_MASTER_KEY:?Error: ASSETVISTA_MASTER_KEY must be set}"
         - "SETTINGS_ADMIN_PASSWORD=${SETTINGS_ADMIN_PASSWORD:?Error: SETTINGS_ADMIN_PASSWORD must be set}"
         - TZ=Asia/Shanghai

     frontend:
       image: carman5012/aliyun-dashboard-frontend:latest
       container_name: aliyun-dashboard-frontend
       restart: always
       ports:
         - "81:80"
       environment:
         - "SETTINGS_ADMIN_PASSWORD=${SETTINGS_ADMIN_PASSWORD:?Error: SETTINGS_ADMIN_PASSWORD must be set}"
       depends_on:
         - backend
   ```

4. **一键拉取与启动**：
   ```bash
   docker-compose -f docker-compose.prod.yml pull
   docker-compose -f docker-compose.prod.yml up -d
   ```

---

### 3. 本地开发与源码构建部署

如果您拉取了完整源码，可以直接在根目录构建启动：

```bash
# 复制并修改环境变量配置
cp .env.example .env

# 构建并启动服务
docker-compose up --build -d
```

---

### 4. 访问系统
* 浏览器打开：`http://<服务器IP或localhost>:81`
* 首次使用请进入 **「账号管理」** 页面添加您的阿里云 AccessKey。
* 系统设置页口令即为 `.env` 中配置的 `SETTINGS_ADMIN_PASSWORD`。

---

## 🛠️ 镜像构建与发布指南

如需重新构建 Docker 镜像并推送到 Docker Hub：

```bash
# 1. 登录 Docker Hub
docker login -u carman5012

# 2. 构建并推送后端
docker build -t carman5012/aliyun-dashboard-backend:latest ./backend
docker push carman5012/aliyun-dashboard-backend:latest

# 3. 构建并推送前端
docker build -t carman5012/aliyun-dashboard-frontend:latest ./frontend
docker push carman5012/aliyun-dashboard-frontend:latest
```

---

## 📂 目录结构

```text
aliyun_dashboard/
├── backend/                           # Python FastAPI 后端服务
│   ├── app/
│   │   ├── api/v1/                    # API 控制器 (账号、资产、系统设置)
│   │   ├── core/                      # 核心配置与 Fernet 密钥加解密模块
│   │   ├── crud/                      # 数据库 CRUD 操作
│   │   ├── db/                        # 数据库连接与 Session 管理 (支持 SQLite / MySQL)
│   │   ├── models/                    # SQLAlchemy 数据模型
│   │   ├── schemas/                   # Pydantic 请求/响应模型定义
│   │   └── tasks/                     # 阿里云同步引擎、APScheduler 调度与域名告警
│   ├── requirements.txt               # 后端依赖清单
│   └── Dockerfile                     # 后端轻量化容器构建文件
├── frontend/                          # Vue 3 + Vite + TypeScript 前端工程
│   ├── src/
│   │   ├── api/                       # 后端 API 接口封装
│   │   ├── assets/                    # 全局 Tailwind 与动画样式
│   │   ├── components/                # 布局、统计卡片、导航组件
│   │   ├── store/                     # Pinia 状态管理 (资源、通知、同步状态)
│   │   └── views/                     # 概览看板、资产列表、账号管理、同步中心、系统设置
│   ├── nginx.conf                     # Nginx 反向代理与环境变量注入配置
│   └── Dockerfile                     # 前端多阶段极简构建文件
├── docker-compose.yml                 # 源码构建本地运行编排文件
├── docker-compose.prod.yml            # 生产环境预编译镜像编排文件
├── generate_key.py                    # 主密钥生成工具
└── README.md                          # 项目文档
```

---

## 🛡️ 安全规范

* **密钥落盘加密**：数据库中存储的所有云账号 Secret Key 均为强加密密文。
* **脱敏与最小权限**：API 返回数据中 AccessKey 会自动掩码处理，加解密只在抓取任务内部瞬时完成。
* **代码与镜像防护**：`.dockerignore` 与 `.gitignore` 均已深度配置，杜绝任何 `.env`、本地数据库、测试文件或密钥凭证被意外打包或推送到远程仓库。
# 阿里云资源看板 (Aliyun Resource Dashboard)

本项目是一个高度自动化、高颜值的多账号云资源聚合监控与管理面板。支持通过 API 自动拉取和汇总展示阿里云的 **ECS 实例、弹性公网 IP (EIP)、域名资产** 以及 **SSL 证书**，并提供实时同步状态、秒级计时器和零资产引导等 Premium 级用户体验。

---

## 🎨 系统特色
1. **多账号级联整合**：一站式配置和管理多个阿里云 AccessKey，数据拉取合并展示，支持账号维度快速筛选过滤。
2. **定时自动同步 (Celery Beat)**：支持在页面上直接调整每个云账号的“自动数据同步频率”（如手动、每小时、每天等），后台异步检测调度。
3. **秒级实时同步计时器**：手动触发资产同步时，主内容区会呈现精致的毛玻璃 Banner，伴随**秒级递增的耗时计时器**，实时展示轮询的 Celery 后台状态。
4. **级联安全清理**：当删除或更新账号别名时，系统会自动删除对应的孤立资产，或自动更新旧资产的归属关系，彻底避免脏数据和重复数据。
5. **暗黑模式支持**：配备极具设计感的主题切换，所有 Naive UI 组件及自定义 Tailwind 样式均完美适配深/浅色模式。

---

## 📂 目录结构与文件说明

```text
aliyun_dashboard/
├── backend/                           # Python 后端微服务
│   ├── app/
│   │   ├── api/                       # RESTful API 路由模块
│   │   │   ├── router.py              # API 路由器总线 (挂载 accounts 和 resources)
│   │   │   └── v1/
│   │   │       ├── accounts.py        # 云账号配置接口 (列表、创建、删除、立即同步)
│   │   │       └── resources.py       # 云资源查询、全局搜索及 Celery 状态查询接口
│   │   ├── core/                      # 核心模块
│   │   │   ├── config.py              # 系统配置类 (连接池参数、敏感信息 fallback)
│   │   │   └── security.py            # 基于 Fernet 的 SK 双向安全加解密机制
│   │   ├── crud/                      # 数据库 CRUD 实现
│   │   │   ├── crud_account.py        # 云账号 CRUD (支持资源别名级联更新与删除级联清理)
│   │   │   └── crud_resource.py       # 统一资源检索与全局模糊搜索
│   │   ├── db/                        # 数据库连接
│   │   │   ├── base.py                # ORM 声明基类 Base
│   │   │   └── session.py             # 数据库 Session 本地依赖生成器 (get_db)
│   │   ├── models/                    # SQLAlchemy 模型
│   │   │   ├── account.py             # 阿里云凭证账号表 (密文存储 Secret Key)
│   │   │   └── resource.py            # 各类云资源表 (Details 以 JSON 动态格式存储)
│   │   ├── schemas/                   # Pydantic 实体传输类 (校验及过滤)
│   │   │   ├── account.py             # 账号创建、更新与响应模型定义
│   │   │   └── resource.py            # 资产信息、数据库空状态响应模型
│   │   └── tasks/                     # 异步及调度模块
│   │       ├── celery_app.py          # Celery 实例定义与 Beat 定时同步频率注册
│   │       └── aliyun_sync.py         # 阿里云 API 交互逻辑与同步 Celery Tasks 定义
│   ├── requirements.txt               # 后端 Python 依赖包清单
│   └── Dockerfile                     # 后端容器构建文件 (依赖预装、时区锁定、启动入口)
├── frontend/                          # Vite + Vue 3 + TS 前端工程
│   ├── src/
│   │   ├── api/
│   │   │   └── index.ts               # 基于 Axios 封装的统一前后端数据交互中心
│   │   ├── assets/
│   │   │   └── main.css               # 全局样式控制 (含自定义动画与暗黑主题转换样式)
│   │   ├── components/                # 可复用组件目录
│   │   │   ├── AccountManager.vue     # 账号管理视图 (账号增删改查、独立同步、修改频率)
│   │   │   ├── ResourceTable.vue      # 资产数据表 (支持数据分类、搜索展示、元数据弹窗)
│   │   │   ├── Sidebar.vue            # 可折叠左侧系统导航栏
│   │   │   └── StatCards.vue          # 四大资产概览指标统计卡片
│   │   ├── router/
│   │   │   └── index.ts               # Vue Router SPA 路由规则 (SPA 模式)
│   │   ├── store/
│   │   │   └── index.ts               # Pinia 状态库 (包含轮询同步状态、秒级计时器逻辑)
│   │   └── views/
│   │       └── Dashboard.vue          # 看板主容器 (顶栏、通知 Banner、多态空状态引导)
│   ├── index.html                     # 静态页面容器主入口 (设定项目标题)
│   ├── nginx.conf                     # Nginx 配置 (SPA 路由分发及后端 API 动态反代)
│   └── Dockerfile                     # 前端多阶段构建文件 (Node.js 编译 -> Nginx 部署)
├── docker-compose.yml                 # 多容器联合部署编排文件 (锁定容器依赖顺序与变量)
├── generate_key.py                    # 快速生成 ASSETVISTA_MASTER_KEY 安全主密钥的工具
└── README.md                          # 项目架构与部署指南说明书
```

---

## 🚀 快速开始与部署

本项目已实现完全的容器化，通过 Docker Compose 可以实现一键式多层容器部署。

### 1. 生成安全加密主密钥 (Master Key)
后端会对用户的 AccessKey Secret 采用安全 AES-256-CBC 算法加密落盘。在首次启动前，需要在宿主机生成密钥：
```bash
python generate_key.py
```
它会输出一个类似如下的 Base64 格式密钥：
```text
vtS4rVskX7eL9qP2mK6b5H8w3d1yG4hL0p3s5t6w7x8=
```

### 2. 启动 Docker 容器服务
您可以将刚刚生成的密钥设置为环境变量，也可以直接通过 Docker Compose 默认值（提供本地开发 fallback）运行。
在项目根目录下执行：
```bash
docker compose up --build -d
```
启动后容器包含：
* `aliyun-dashboard-db` (MySQL 8.0)
* `aliyun-dashboard-redis` (Redis 缓存与 Celery 消息队列)
* `aliyun-dashboard-backend` (FastAPI 接口服务，自动重试连通数据库建表)
* `aliyun-dashboard-worker` (Celery 异步工作流及 Beat 定时同步调度器)
* `aliyun-dashboard-frontend` (Nginx 托管的前端单页应用，暴露宿主机 `81` 端口)
### 3. 访问面板
打开浏览器，访问：
```text
http://localhost:81
```
即可开始查看各类云资源，并在左下角 **「云账号管理」** 里新增、删除或调整您的阿里云凭证及自动同步频率。

---

## 🛡️ 安全合规说明
* **凭证加解密**：项目中所有的 `AccessKey Secret` 均在后端执行 AES-256 加密后再写入数据库。
* **密钥混淆**：解密行为仅限在 `celery_worker` 执行抓取任务时进行，**用完即焚**，绝不通过任何 API 接口流向前端，前端回显 AK 时会进行掩码脱敏处理。
FROM python:3.10-slim

WORKDIR /app

# 安装必要的系统依赖（如果涉及 mysql 客户端等可以添加）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && mkdir /app/data \
    && rm -rf /var/lib/apt/lists/*


# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

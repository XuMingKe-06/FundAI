FROM python:3.12-slim

WORKDIR /app

# 安装 Node.js
RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装前端依赖
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm install

# 复制应用代码
COPY . .

# 创建数据目录（Chroma 向量数据库持久化目录）
RUN mkdir -p data/chroma

# 暴露端口
EXPOSE 8000 3000

# 启动命令
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 & cd frontend && npm run dev & wait"]

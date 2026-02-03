# 使用官方 Python 镜像作为基础镜像
FROM python:3.10-slim

# 设置工作目录为 /app
WORKDIR /app

# 复制 requirements.txt 文件（如果有）
COPY requirements.txt .

# 安装项目的依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制当前目录下的所有文件到容器的 /app 目录
COPY . .

# 暴露端口（如果应用使用某个端口，比如 Flask 的 5000 端口）
EXPOSE 5000

# 启动应用（如果是 Flask 应用，可以使用 Flask 的命令）
CMD ["python", "app.py"]


# 指定基础镜像为 Python 3.11
FROM python:3.11
# 设置工作目录
WORKDIR /app

# 替换为国内源
RUN mkdir -p ~/.pip \
    && echo "[global]" > ~/.pip/pip.conf \
    && echo "index-url=https://mirrors.aliyun.com/pypi/simple" >> ~/.pip/pip.conf \
    && echo "trusted-host=mirrors.aliyun.com" >> ~/.pip/pip.conf

RUN python -m pip install --upgrade pip


# 将当前目录下的 requirements.txt 文件复制到容器内的工作目录
COPY requirements.txt .


# 安装依赖
RUN pip install -r requirements.txt

# 将当前目录下的项目代码复制到容器内的工作目录
COPY . .

# 设置环境变量
ENV DJANGO_SETTINGS_MODULE=mysite.settings

# 暴露容器内的端口
EXPOSE 8002

# 运行 Django 命令来启动服务器
CMD ["python", "manage.py", "runserver", "0.0.0.0:8002"]
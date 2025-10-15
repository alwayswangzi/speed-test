# 下载速度测试工具

这是一个用于测试网络下载速度的Web应用程序

## 功能特性

- 提供美观的Web界面
- 支持多种文件大小测试：1MB、10MB、50MB、100MB
- 实时显示下载进度
- 计算平均速度和峰值速度
- 网络延迟和服务器响应时间测试

## 安装和运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行服务器

#### 方式一：直接运行（开发环境）

```bash
python3 speed_test.py
```

#### 方式二：后台运行（推荐）

```bash
# 启动后台服务
./start.sh start

# 查看服务状态
./start.sh status

# 停止服务
./start.sh stop

# 重启服务
./start.sh restart
```

#### 方式三：系统服务（生产环境）

```bash
# 安装为系统服务（需要root权限）
sudo ./start.sh install

# 使用systemd管理
sudo systemctl start speed_test
sudo systemctl enable speed_test  # 开机自启
```

### 3. 访问测试页面

打开浏览器访问: http://localhost:5000

## Nginx反向代理设置

### 1. 安装Nginx
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y nginx

# CentOS/RHEL
sudo yum install -y nginx

# 启动并设置开机自启：
sudo systemctl enable nginx
sudo systemctl start nginx
```

### 2. 配置 Nginx 反向代理

编辑默认站点配置：

```bash
sudo vim /etc/nginx/sites-available/default
```

修改 server 块，添加 location /speedtest/ 代理规则

```Nginx
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    # 根目录（可选）
    root /var/www/html;
    index index.html;

    # 反向代理：将 /speed-test/ 请求转发到 localhost:5000
    location /speed-test/ {
        # 注意：目标地址末尾的 / 很重要
        proxy_pass http://127.0.0.1:5000/;

        # 传递真实客户端信息
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 设置超时
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;

        # 支持 WebSocket（如果后端需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 其他 location（如根路径）
    location / {
        # 可选：显示欢迎页或静态内容
        try_files $uri $uri/ =404;
    }
}
```

### 3. 测试配置并重启 Nginx

```bash
# 测试配置是否正确
sudo nginx -t

# 输出应为：
# nginx: configuration file /etc/nginx/nginx.conf syntax is ok
# nginx: configuration file /etc/nginx/nginx.conf test is successful

# 重新加载 Nginx
sudo systemctl reload nginx
```
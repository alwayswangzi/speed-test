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

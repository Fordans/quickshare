# QuickShare - 局域网文件快传工具

一个简单易用的局域网文件传输工具，支持文件上传和下载，无需登录微信/QQ，也无需数据线。

## 功能特点

-  **文件上传**：支持网页端拖拽上传文件到服务器当前目录
-  **文件下载**：支持下载服务器目录中的所有文件
-  **密码保护**：可选的 `--auth` 参数设置临时访问密码
-  **二维码显示**：自动生成二维码，方便手机扫码访问
-  **美观界面**：现代化的 Web 界面，支持移动端
-  **自动刷新**：文件列表自动刷新，无需手动刷新页面

## 安装

1. 确保已安装 Python 3.6+

2. 安装依赖：
```bash
pip install -r requirements.txt
```

或者直接安装：
```bash
pip install Flask qrcode[pil]
```

## 使用方法

### 基本用法

```bash
# 启动服务器（无密码，默认端口 8000）
python quickshare.py

# 指定端口
python quickshare.py --port 8080

# 指定文件目录
python quickshare.py --dir /path/to/directory

# 设置访问密码
python quickshare.py --auth mypassword

# 不显示二维码
python quickshare.py --no-qr
```

### 完整示例

```bash
# 启动带密码保护的服务器，端口 8080，指定目录
python quickshare.py --port 8080 --dir ./uploads --auth mypass123
```

## 使用场景

1. **手机传照片给电脑**：
   - 在电脑上运行 `python quickshare.py`
   - 手机连接同一 WiFi
   - 手机浏览器访问显示的 IP 地址
   - 拖拽照片上传

2. **两台电脑互传文件**：
   - 在接收文件的电脑上运行服务器
   - 发送方电脑浏览器访问服务器地址
   - 上传文件即可

3. **临时文件共享**：
   - 在需要共享的目录运行服务器
   - 局域网内其他设备访问下载文件

## 安全提示

-  未设置 `--auth` 参数时，服务器对局域网内所有设备开放
-  建议在公共网络环境下使用 `--auth` 参数设置密码
-  使用完毕后请及时停止服务器（Ctrl+C）

## 技术栈

- **Flask**：轻量级 Web 框架
- **qrcode**：二维码生成库
- **Python 标准库**：socket, argparse 等

## 许可证

MIT License


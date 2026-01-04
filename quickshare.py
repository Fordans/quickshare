#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
局域网文件快传工具 (QuickShare)
支持文件上传和下载的临时 Web 服务器
"""

import os
import sys
import socket
import argparse
import secrets
from pathlib import Path
from functools import wraps
from flask import Flask, request, send_file, jsonify, render_template_string, Response
import qrcode
from io import BytesIO
import base64

app = Flask(__name__)
UPLOAD_DIR = os.getcwd()
AUTH_TOKEN = None


def get_local_ip():
    """获取本机局域网 IP 地址"""
    try:
        # 连接到一个远程地址（不实际发送数据）来获取本机 IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def check_auth(token):
    """检查认证令牌"""
    if AUTH_TOKEN is None:
        return True
    return token == AUTH_TOKEN


def requires_auth(f):
    """认证装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if AUTH_TOKEN is not None:
            token = request.cookies.get('auth_token') or request.args.get('token')
            if not token or not check_auth(token):
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'Unauthorized'}), 401
                return render_template_string(LOGIN_PAGE), 401
        return f(*args, **kwargs)
    return decorated


def generate_qr_code(url):
    """生成二维码并返回 base64 编码的图片"""
    qr = qrcode.QRCode(version=1, box_size=2, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return img_str


def print_qr_in_terminal(url):
    """在终端打印二维码（使用 ASCII 字符）"""
    try:
        qr = qrcode.QRCode()
        qr.add_data(url)
        qr.make()
        qr.print_ascii(invert=True)
    except Exception:
        # 如果打印失败，至少显示 URL
        print(f"\n访问地址: {url}\n")


# HTML 模板
LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QuickShare - 需要认证</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #1a1a1a;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }
        .login-container {
            background: #ffffff;
            padding: 48px 40px;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            max-width: 420px;
            width: 100%;
            border: 1px solid #e5e5e5;
        }
        h1 { 
            color: #1a1a1a; 
            margin-bottom: 8px; 
            text-align: center; 
            font-size: 24px;
            font-weight: 600;
            letter-spacing: -0.5px;
        }
        p { 
            color: #666666; 
            margin-bottom: 32px; 
            text-align: center; 
            font-size: 14px;
        }
        input {
            width: 100%;
            padding: 12px 16px;
            border: 1px solid #d0d0d0;
            border-radius: 4px;
            font-size: 14px;
            margin-bottom: 20px;
            background: #ffffff;
            color: #1a1a1a;
            transition: border-color 0.2s;
        }
        input:focus { 
            outline: none; 
            border-color: #1a1a1a; 
        }
        input::placeholder {
            color: #999999;
        }
        button {
            width: 100%;
            padding: 12px 16px;
            background: #1a1a1a;
            color: #ffffff;
            border: none;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        button:hover { background: #2d2d2d; }
        button:active { background: #0d0d0d; }
        .error { 
            color: #d32f2f; 
            margin-top: 12px; 
            text-align: center; 
            font-size: 13px;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>QuickShare</h1>
        <p>请输入访问密码</p>
        <form method="POST" action="/login">
            <input type="password" name="password" placeholder="密码" required autofocus>
            <button type="submit">登录</button>
        </form>
        <div id="error" class="error">{% if error %}{{ error }}{% endif %}</div>
    </div>
</body>
</html>
"""

MAIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QuickShare - 文件快传</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f5f5f5;
            min-height: 100vh;
            padding: 24px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: #ffffff;
            padding: 32px;
            border-radius: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 24px;
            border: 1px solid #e5e5e5;
        }
        h1 { 
            color: #1a1a1a; 
            margin-bottom: 8px; 
            font-size: 28px;
            font-weight: 600;
            letter-spacing: -0.5px;
        }
        .info { 
            color: #666666; 
            font-size: 13px; 
            font-weight: 400;
        }
        .main-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }
        @media (max-width: 768px) {
            .main-content { grid-template-columns: 1fr; }
        }
        .card {
            background: #ffffff;
            padding: 32px;
            border-radius: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid #e5e5e5;
        }
        .card h2 { 
            color: #1a1a1a; 
            margin-bottom: 24px; 
            font-size: 18px;
            font-weight: 600;
            letter-spacing: -0.3px;
        }
        .upload-area {
            border: 2px dashed #d0d0d0;
            border-radius: 4px;
            padding: 48px 32px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
            background: #fafafa;
        }
        .upload-area:hover { 
            border-color: #1a1a1a; 
            background: #f5f5f5; 
        }
        .upload-area.dragover { 
            border-color: #1a1a1a; 
            background: #f0f0f0; 
        }
        .upload-icon { 
            font-size: 32px; 
            margin-bottom: 12px; 
            opacity: 0.4;
            font-weight: 300;
        }
        .upload-area p {
            color: #666666;
            font-size: 14px;
            font-weight: 400;
        }
        .file-input { display: none; }
        .file-list {
            list-style: none;
            margin-top: 0;
        }
        .file-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 14px 16px;
            background: #fafafa;
            border-radius: 4px;
            margin-bottom: 8px;
            border: 1px solid #e5e5e5;
            transition: all 0.2s;
        }
        .file-item:hover { 
            background: #f5f5f5; 
            border-color: #d0d0d0;
        }
        .file-name { 
            flex: 1; 
            color: #1a1a1a; 
            font-size: 14px;
            font-weight: 400;
        }
        .file-size { 
            color: #999999; 
            font-size: 12px; 
            margin-right: 16px;
            font-weight: 400;
        }
        .file-actions a {
            color: #1a1a1a;
            text-decoration: none;
            padding: 6px 16px;
            border-radius: 4px;
            transition: all 0.2s;
            font-size: 13px;
            border: 1px solid #d0d0d0;
            background: #ffffff;
            display: inline-block;
        }
        .file-actions a:hover { 
            background: #1a1a1a; 
            color: #ffffff;
            border-color: #1a1a1a;
        }
        .progress-bar {
            width: 100%;
            height: 4px;
            background: #e5e5e5;
            border-radius: 2px;
            margin-top: 16px;
            overflow: hidden;
            display: none;
        }
        .progress-fill {
            height: 100%;
            background: #1a1a1a;
            width: 0%;
            transition: width 0.3s;
        }
        .upload-status {
            margin-top: 16px;
            padding: 12px 16px;
            border-radius: 4px;
            display: none;
            font-size: 13px;
        }
        .upload-status.success {
            background: #e8f5e9;
            color: #2e7d32;
            display: block;
            border: 1px solid #c8e6c9;
        }
        .upload-status.error {
            background: #ffebee;
            color: #c62828;
            display: block;
            border: 1px solid #ffcdd2;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1> QuickShare 文件快传</h1>
            <p class="info">当前目录: {{ current_dir }}</p>
        </div>
        <div class="main-content">
            <div class="card">
                <h2>上传文件</h2>
                <div class="upload-area" id="uploadArea">
                    <div class="upload-icon">↑</div>
                    <p>拖拽文件到此处或点击选择</p>
                    <input type="file" id="fileInput" class="file-input" multiple>
                </div>
                <div class="progress-bar" id="progressBar">
                    <div class="progress-fill" id="progressFill"></div>
                </div>
                <div class="upload-status" id="uploadStatus"></div>
            </div>
            <div class="card">
                <h2> 下载文件</h2>
                <ul class="file-list" id="fileList">
                    {% for file in files %}
                    <li class="file-item">
                        <span class="file-name">{{ file.name }}</span>
                        <span class="file-size">{{ file.size }}</span>
                        <div class="file-actions">
                            <a href="/download/{{ file.name }}?token={{ token }}" download>下载</a>
                        </div>
                    </li>
                    {% endfor %}
                </ul>
            </div>
        </div>
    </div>
    <script>
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const progressBar = document.getElementById('progressBar');
        const progressFill = document.getElementById('progressFill');
        const uploadStatus = document.getElementById('uploadStatus');
        const token = new URLSearchParams(window.location.search).get('token') || '';

        uploadArea.addEventListener('click', () => fileInput.click());

        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            handleFiles(e.dataTransfer.files);
        });

        fileInput.addEventListener('change', (e) => {
            handleFiles(e.target.files);
        });

        async function handleFiles(files) {
            if (files.length === 0) return;

            progressBar.style.display = 'block';
            uploadStatus.style.display = 'none';
            progressFill.style.width = '0%';

            const formData = new FormData();
            for (let file of files) {
                formData.append('files', file);
            }

            try {
                const xhr = new XMLHttpRequest();
                xhr.upload.addEventListener('progress', (e) => {
                    if (e.lengthComputable) {
                        const percent = (e.loaded / e.total) * 100;
                        progressFill.style.width = percent + '%';
                    }
                });

                xhr.addEventListener('load', () => {
                    progressFill.style.width = '100%';
                    if (xhr.status === 200) {
                        uploadStatus.className = 'upload-status success';
                        uploadStatus.textContent = '上传成功！页面将自动刷新...';
                        setTimeout(() => location.reload(), 1000);
                    } else {
                        uploadStatus.className = 'upload-status error';
                        uploadStatus.textContent = '上传失败: ' + xhr.responseText;
                    }
                });

                xhr.addEventListener('error', () => {
                    uploadStatus.className = 'upload-status error';
                    uploadStatus.textContent = '上传失败，请重试';
                });

                const url = '/upload' + (token ? '?token=' + token : '');
                xhr.open('POST', url);
                xhr.send(formData);
            } catch (error) {
                uploadStatus.className = 'upload-status error';
                uploadStatus.textContent = '上传失败: ' + error.message;
            }
        }

        // 定期刷新文件列表
        setInterval(() => {
            fetch('/api/files' + (token ? '?token=' + token : ''))
                .then(r => r.json())
                .then(data => {
                    const fileList = document.getElementById('fileList');
                    fileList.innerHTML = data.files.map(file => `
                        <li class="file-item">
                            <span class="file-name">${file.name}</span>
                            <span class="file-size">${file.size}</span>
                            <div class="file-actions">
                                <a href="/download/${encodeURIComponent(file.name)}?token=${token}" download>下载</a>
                            </div>
                        </li>
                    `).join('');
                })
                .catch(err => console.error('刷新文件列表失败:', err));
        }, 5000);
    </script>
</body>
</html>
"""


@app.route('/')
@requires_auth
def index():
    """主页面"""
    files = []
    for item in os.listdir(UPLOAD_DIR):
        item_path = os.path.join(UPLOAD_DIR, item)
        if os.path.isfile(item_path):
            size = os.path.getsize(item_path)
            size_str = format_size(size)
            files.append({'name': item, 'size': size_str})
    
    token = request.cookies.get('auth_token') or request.args.get('token', '')
    return render_template_string(MAIN_PAGE, files=files, current_dir=UPLOAD_DIR, token=token)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if AUTH_TOKEN is None:
        return '', 404
    
    error = request.args.get('error')
    
    if request.method == 'POST':
        password = request.form.get('password')
        if password == AUTH_TOKEN:
            resp = Response('', 302)
            resp.headers['Location'] = '/?token=' + AUTH_TOKEN
            resp.set_cookie('auth_token', AUTH_TOKEN, max_age=3600)
            return resp
        else:
            resp = Response('', 302)
            resp.headers['Location'] = '/login?error=密码错误，请重试'
            return resp
    
    return render_template_string(LOGIN_PAGE, error=error)


@app.route('/upload', methods=['POST'])
@requires_auth
def upload():
    """文件上传接口"""
    if 'files' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    
    files = request.files.getlist('files')
    uploaded = []
    
    for file in files:
        if file.filename:
            filename = file.filename
            # 防止路径遍历攻击
            filename = os.path.basename(filename)
            filepath = os.path.join(UPLOAD_DIR, filename)
            file.save(filepath)
            uploaded.append(filename)
    
    return jsonify({'message': '上传成功', 'files': uploaded})


@app.route('/download/<filename>')
@requires_auth
def download(filename):
    """文件下载接口"""
    # 防止路径遍历攻击
    filename = os.path.basename(filename)
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    if not os.path.isfile(filepath):
        return jsonify({'error': '文件不存在'}), 404
    
    return send_file(filepath, as_attachment=True)


@app.route('/api/files')
@requires_auth
def api_files():
    """获取文件列表 API"""
    files = []
    for item in os.listdir(UPLOAD_DIR):
        item_path = os.path.join(UPLOAD_DIR, item)
        if os.path.isfile(item_path):
            size = os.path.getsize(item_path)
            size_str = format_size(size)
            files.append({'name': item, 'size': size_str})
    
    return jsonify({'files': files})


def format_size(size):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def main():
    global UPLOAD_DIR, AUTH_TOKEN
    
    parser = argparse.ArgumentParser(
        description='局域网文件快传工具 - 支持上传和下载的临时 Web 服务器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python quickshare.py                    # 启动服务器（无密码）
  python quickshare.py --auth mypass      # 启动服务器（需要密码）
  python quickshare.py --port 8080        # 指定端口
  python quickshare.py --dir /path/to/dir # 指定目录
        """
    )
    parser.add_argument('--port', type=int, default=8000, help='服务器端口 (默认: 8000)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='服务器地址 (默认: 0.0.0.0)')
    parser.add_argument('--dir', type=str, help='文件目录 (默认: 当前目录)')
    parser.add_argument('--auth', type=str, help='访问密码（设置后需要密码才能访问）')
    parser.add_argument('--no-qr', action='store_true', help='不显示二维码')
    
    args = parser.parse_args()
    
    if args.dir:
        UPLOAD_DIR = os.path.abspath(args.dir)
        if not os.path.isdir(UPLOAD_DIR):
            print(f"错误: 目录不存在: {UPLOAD_DIR}")
            sys.exit(1)
    else:
        UPLOAD_DIR = os.getcwd()
    
    if args.auth:
        AUTH_TOKEN = args.auth
        print(f"🔒 已启用密码保护，密码: {AUTH_TOKEN}")
    else:
        AUTH_TOKEN = None
        print("⚠️  未设置密码，服务器对局域网内所有设备开放")
    
    local_ip = get_local_ip()
    protocol = 'http'
    url = f"{protocol}://{local_ip}:{args.port}"
    
    if AUTH_TOKEN:
        url_with_auth = f"{url}/?token={AUTH_TOKEN}"
    else:
        url_with_auth = url
    
    print(f"\n{'='*60}")
    print(f" QuickShare 文件快传服务器已启动")
    print(f"{'='*60}")
    print(f" 服务目录: {UPLOAD_DIR}")
    print(f" 访问地址: {url}")
    if AUTH_TOKEN:
        print(f" 访问密码: {AUTH_TOKEN}")
        print(f" 完整链接: {url_with_auth}")
    print(f"{'='*60}\n")
    
    if not args.no_qr:
        print("二维码:")
        print_qr_in_terminal(url_with_auth)
        print("\n")
    
    print("按 Ctrl+C 停止服务器\n")
    
    try:
        app.run(host=args.host, port=args.port, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n\n服务器已停止")
        sys.exit(0)


if __name__ == '__main__':
    main()


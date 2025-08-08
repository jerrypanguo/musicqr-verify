#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化测试版本 - 用于排查问题
"""

from flask import Flask, jsonify
import os
import sys

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(__file__))

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({
        'status': 'running',
        'message': 'Test API is working',
        'python_path': sys.path[:3],
        'current_dir': os.getcwd(),
        'files': os.listdir('.')
    })

@app.route('/api/status')
def api_status():
    return jsonify({
        'status': 'running',
        'timestamp': '2024-01-01T00:00:00',
        'stats': {
            'total_codes': 0,
            'activated_codes': 0,
            'activation_rate': 0,
            'today_queries': 0
        }
    })

if __name__ == '__main__':
    print("Starting test app...")
    print(f"Current directory: {os.getcwd()}")
    print(f"Files in directory: {os.listdir('.')}")
    app.run(host='0.0.0.0', port=5000, debug=True)

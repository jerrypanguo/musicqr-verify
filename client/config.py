#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
客户端配置文件
"""

import os
import hashlib
import hmac

class ClientConfig:
    """客户端配置类"""
    
    # VPS服务器配置
    VPS_URL = os.environ.get('VPS_URL', 'https://verify.yuzeguitar.me')
    
    # API密钥配置
    # 注意：这个密钥需要与服务器端的密钥匹配
    SECRET_KEY = os.environ.get('CLIENT_SECRET_KEY', 'your-secret-key-here')
    API_KEY_SALT = os.environ.get('API_KEY_SALT', 'musicqr_api_salt_2024')
    
    # 生成API密钥
    @property
    def API_KEY(self):
        """动态生成API密钥"""
        return hmac.new(
            self.SECRET_KEY.encode(),
            self.API_KEY_SALT.encode(),
            hashlib.sha256
        ).hexdigest()
    
    # 本地文件配置
    OUTPUT_DIR = 'output'
    DATA_DIR = 'data'
    
    # PDF配置
    DEFAULT_ORIENTATION = 'landscape'  # 'landscape' 或 'portrait'
    DEFAULT_COUNT = 50
    
    # 网络配置
    REQUEST_TIMEOUT = 30  # 请求超时时间（秒）
    MAX_RETRIES = 3       # 最大重试次数
    
    # 二维码配置
    QR_VERSION = 1
    QR_ERROR_CORRECTION = 'L'  # L, M, Q, H
    QR_BOX_SIZE = 10
    QR_BORDER = 4
    
    # 验证码配置
    CODE_LENGTH = 12
    CODE_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # 排除容易混淆的字符
    
    @classmethod
    def validate_config(cls):
        """验证配置"""
        errors = []
        
        if not cls.VPS_URL:
            errors.append("VPS_URL 未配置")
        
        if not cls.SECRET_KEY or cls.SECRET_KEY == 'your-secret-key-here':
            errors.append("SECRET_KEY 未正确配置")
        
        if cls.CODE_LENGTH < 8 or cls.CODE_LENGTH > 20:
            errors.append("CODE_LENGTH 应该在 8-20 之间")
        
        return errors
    
    @classmethod
    def print_config(cls):
        """打印当前配置"""
        print("=== 客户端配置 ===")
        print(f"VPS地址: {cls.VPS_URL}")
        print(f"API密钥: {cls().API_KEY[:8]}...")
        print(f"输出目录: {cls.OUTPUT_DIR}")
        print(f"数据目录: {cls.DATA_DIR}")
        print(f"默认PDF格式: {cls.DEFAULT_ORIENTATION}")
        print(f"默认生成数量: {cls.DEFAULT_COUNT}")
        print(f"验证码长度: {cls.CODE_LENGTH}")
        
        # 验证配置
        errors = cls.validate_config()
        if errors:
            print("\n⚠️ 配置问题:")
            for error in errors:
                print(f"  - {error}")
        else:
            print("\n✅ 配置验证通过")

# 开发环境配置
class DevelopmentConfig(ClientConfig):
    """开发环境配置"""
    VPS_URL = 'http://localhost:5000'
    SECRET_KEY = 'dev-secret-key-2024'

# 生产环境配置
class ProductionConfig(ClientConfig):
    """生产环境配置"""
    VPS_URL = 'https://verify.yuzeguitar.me'
    # 生产环境必须从环境变量读取密钥
    SECRET_KEY = os.environ.get('CLIENT_SECRET_KEY')
    
    @classmethod
    def validate_config(cls):
        errors = super().validate_config()
        
        if not cls.SECRET_KEY:
            errors.append("生产环境必须设置 CLIENT_SECRET_KEY 环境变量")
        
        if not cls.VPS_URL.startswith('https://'):
            errors.append("生产环境必须使用 HTTPS")
        
        return errors

# 配置选择
def get_config(env=None):
    """获取配置类"""
    if env is None:
        env = os.environ.get('CLIENT_ENV', 'production')
    
    if env == 'development':
        return DevelopmentConfig
    else:
        return ProductionConfig

if __name__ == '__main__':
    # 测试配置
    print("=== 配置测试 ===")
    
    # 获取当前配置
    config_class = get_config()
    config = config_class()
    
    # 打印配置信息
    config_class.print_config()
    
    # 测试API密钥生成
    print(f"\n生成的API密钥: {config.API_KEY}")
    
    # 显示环境变量设置示例
    print("\n=== 环境变量设置示例 ===")
    print("# 生产环境")
    print("export CLIENT_ENV='production'")
    print("export VPS_URL='https://verify.yuzeguitar.me'")
    print("export CLIENT_SECRET_KEY='your-actual-secret-key'")
    print("export API_KEY_SALT='musicqr_api_salt_2024'")
    
    print("\n# 开发环境")
    print("export CLIENT_ENV='development'")
    print("export VPS_URL='http://localhost:5000'")
    print("export CLIENT_SECRET_KEY='dev-secret-key-2024'")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件
"""

import os
import secrets
from datetime import timedelta

class Config:
    """应用配置类"""
    
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # 数据库配置
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or 'data/musicqr.db'
    
    # API配置
    API_KEY_SALT = os.environ.get('API_KEY_SALT') or 'musicqr_api_salt_2024'
    
    # 安全配置
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/musicqr_api.log')
    
    # 备份配置
    BACKUP_DIR = os.environ.get('BACKUP_DIR', 'backups')
    BACKUP_RETENTION_DAYS = int(os.environ.get('BACKUP_RETENTION_DAYS', '30'))
    
    # 限流配置
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', '100 per hour')
    
    # CORS配置
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        # 确保必要的目录存在
        dirs_to_create = [
            os.path.dirname(Config.DATABASE_PATH),
            os.path.dirname(Config.LOG_FILE),
            Config.BACKUP_DIR
        ]
        
        for dir_path in dirs_to_create:
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    DATABASE_PATH = 'data/musicqr_dev.db'
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    
    # 生产环境使用更安全的配置
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("生产环境必须设置 SECRET_KEY 环境变量")
    
    # 数据库路径
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or '/var/lib/musicqr/musicqr.db'
    
    # 日志配置
    LOG_FILE = os.environ.get('LOG_FILE') or '/var/log/musicqr/api.log'
    
    # 备份配置
    BACKUP_DIR = os.environ.get('BACKUP_DIR') or '/var/backups/musicqr'

class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DATABASE_PATH = ':memory:'  # 使用内存数据库
    LOG_LEVEL = 'DEBUG'

# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(config_name=None):
    """获取配置类"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    return config.get(config_name, config['default'])

# API密钥生成工具
def generate_api_key(secret_key: str = None, salt: str = None) -> str:
    """
    生成API密钥
    
    Args:
        secret_key: 密钥种子
        salt: 盐值
        
    Returns:
        str: API密钥
    """
    import hashlib
    import hmac
    
    if not secret_key:
        secret_key = Config.SECRET_KEY
    if not salt:
        salt = Config.API_KEY_SALT
    
    return hmac.new(
        secret_key.encode(),
        salt.encode(),
        hashlib.sha256
    ).hexdigest()

if __name__ == '__main__':
    # 测试配置
    print("=== 配置测试 ===")
    
    # 显示当前配置
    current_config = get_config()
    print(f"当前配置: {current_config.__name__}")
    print(f"DEBUG: {current_config.DEBUG}")
    print(f"数据库路径: {current_config.DATABASE_PATH}")
    print(f"日志文件: {current_config.LOG_FILE}")
    
    # 生成API密钥
    api_key = generate_api_key()
    print(f"\nAPI密钥: {api_key}")
    print(f"请将此密钥配置到客户端中")
    
    # 显示环境变量示例
    print("\n=== 环境变量示例 ===")
    print("# 生产环境")
    print(f"export SECRET_KEY='{secrets.token_hex(32)}'")
    print(f"export API_KEY_SALT='musicqr_api_salt_2024'")
    print("export FLASK_ENV='production'")
    print("export DATABASE_PATH='/var/lib/musicqr/musicqr.db'")
    print("export LOG_FILE='/var/log/musicqr/api.log'")
    print("export BACKUP_DIR='/var/backups/musicqr'")
    
    print("\n# 开发环境")
    print("export FLASK_ENV='development'")
    print("export FLASK_DEBUG='true'")

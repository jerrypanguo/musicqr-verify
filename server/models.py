#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库模型和初始化
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, Dict, List

class AuthCode:
    """授权码模型"""
    
    def __init__(self, code: str, created_date: str = None):
        self.code = code.upper().strip()
        self.created_date = created_date or datetime.now().isoformat()
        self.activated = False
        self.activation_date = None
        self.activation_ip = None
        self.activation_user_agent = None
        self.query_count = 0
        self.last_query_date = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'code': self.code,
            'created_date': self.created_date,
            'activated': self.activated,
            'activation_date': self.activation_date,
            'activation_ip': self.activation_ip,
            'activation_user_agent': self.activation_user_agent,
            'query_count': self.query_count,
            'last_query_date': self.last_query_date
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AuthCode':
        """从字典创建实例"""
        auth_code = cls(data['code'], data.get('created_date'))
        auth_code.activated = data.get('activated', False)
        auth_code.activation_date = data.get('activation_date')
        auth_code.activation_ip = data.get('activation_ip')
        auth_code.activation_user_agent = data.get('activation_user_agent')
        auth_code.query_count = data.get('query_count', 0)
        auth_code.last_query_date = data.get('last_query_date')
        return auth_code

def init_db(db_path: str = 'musicqr.db'):
    """
    初始化数据库
    
    Args:
        db_path: 数据库文件路径
    """
    # 确保数据库目录存在
    db_dir = os.path.dirname(os.path.abspath(db_path))
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建授权码表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auth_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code VARCHAR(12) UNIQUE NOT NULL,
            created_date DATETIME NOT NULL,
            activated BOOLEAN DEFAULT FALSE,
            activation_date DATETIME NULL,
            activation_ip VARCHAR(45) NULL,
            activation_user_agent TEXT NULL,
            query_count INTEGER DEFAULT 0,
            last_query_date DATETIME NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建索引以提高查询性能
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_code ON auth_codes(code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_activated ON auth_codes(activated)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_activation_date ON auth_codes(activation_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_last_query_date ON auth_codes(last_query_date)')
    
    # 创建查询日志表（可选，用于详细统计）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS query_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code VARCHAR(12) NOT NULL,
            client_ip VARCHAR(45),
            user_agent TEXT,
            query_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            result VARCHAR(20) NOT NULL,
            FOREIGN KEY (code) REFERENCES auth_codes(code)
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_query_time ON query_logs(query_time)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_query_code ON query_logs(code)')
    
    conn.commit()
    conn.close()
    
    print(f"✅ 数据库初始化完成: {db_path}")

def backup_database(db_path: str = 'musicqr.db', backup_dir: str = 'backups'):
    """
    备份数据库
    
    Args:
        db_path: 数据库文件路径
        backup_dir: 备份目录
    """
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    # 创建备份目录
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # 生成备份文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"musicqr_backup_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    try:
        # 使用SQLite的备份API
        source = sqlite3.connect(db_path)
        backup = sqlite3.connect(backup_path)
        source.backup(backup)
        backup.close()
        source.close()
        
        print(f"✅ 数据库备份完成: {backup_path}")
        return True
        
    except Exception as e:
        print(f"❌ 数据库备份失败: {e}")
        return False

def get_database_stats(db_path: str = 'musicqr.db') -> Dict:
    """
    获取数据库统计信息
    
    Args:
        db_path: 数据库文件路径
        
    Returns:
        Dict: 统计信息
    """
    if not os.path.exists(db_path):
        return {}
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        stats = {}
        
        # 总授权码数量
        cursor.execute("SELECT COUNT(*) FROM auth_codes")
        stats['total_codes'] = cursor.fetchone()[0]
        
        # 已激活数量
        cursor.execute("SELECT COUNT(*) FROM auth_codes WHERE activated = TRUE")
        stats['activated_codes'] = cursor.fetchone()[0]
        
        # 激活率
        if stats['total_codes'] > 0:
            stats['activation_rate'] = round(stats['activated_codes'] / stats['total_codes'] * 100, 2)
        else:
            stats['activation_rate'] = 0
        
        # 今日查询数量
        today = datetime.now().date().isoformat()
        cursor.execute("SELECT COUNT(*) FROM auth_codes WHERE DATE(last_query_date) = ?", (today,))
        stats['today_queries'] = cursor.fetchone()[0]
        
        # 本周激活数量
        cursor.execute("""
            SELECT COUNT(*) FROM auth_codes 
            WHERE activated = TRUE 
            AND DATE(activation_date) >= DATE('now', '-7 days')
        """)
        stats['week_activations'] = cursor.fetchone()[0]
        
        # 最近激活的授权码
        cursor.execute("""
            SELECT code, activation_date 
            FROM auth_codes 
            WHERE activated = TRUE 
            ORDER BY activation_date DESC 
            LIMIT 5
        """)
        recent_activations = cursor.fetchall()
        stats['recent_activations'] = [
            {'code': row[0], 'activation_date': row[1]} 
            for row in recent_activations
        ]
        
        # 数据库文件大小
        stats['db_size_mb'] = round(os.path.getsize(db_path) / (1024 * 1024), 2)
        
        return stats
        
    except Exception as e:
        print(f"❌ 获取数据库统计失败: {e}")
        return {}
    
    finally:
        conn.close()

def cleanup_old_logs(db_path: str = 'musicqr.db', days: int = 30):
    """
    清理旧的查询日志
    
    Args:
        db_path: 数据库文件路径
        days: 保留天数
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            DELETE FROM query_logs 
            WHERE query_time < DATE('now', '-{} days')
        """.format(days))
        
        deleted_count = cursor.rowcount
        conn.commit()
        
        print(f"✅ 清理了 {deleted_count} 条旧日志记录")
        
    except Exception as e:
        print(f"❌ 清理日志失败: {e}")
    
    finally:
        conn.close()

if __name__ == '__main__':
    # 测试数据库初始化
    print("初始化数据库...")
    init_db()
    
    # 显示统计信息
    print("\n数据库统计:")
    stats = get_database_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # 测试备份
    print("\n测试备份...")
    backup_database()

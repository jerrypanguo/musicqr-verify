#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
乐谱二维码验证系统 - 系统测试脚本
用于测试系统各个组件的功能
"""

import requests
import json
import sqlite3
import os
import sys
import time
from datetime import datetime
import hashlib
import hmac
import argparse

class SystemTester:
    """系统测试类"""
    
    def __init__(self, vps_url="http://localhost:5000", api_key=None):
        self.vps_url = vps_url.rstrip('/')
        self.api_key = api_key or self.generate_test_api_key()
        self.test_codes = []
        self.results = []
    
    def generate_test_api_key(self):
        """生成测试API密钥"""
        secret_key = "test-secret-key-2024"
        salt = "musicqr_api_salt_2024"
        return hmac.new(
            secret_key.encode(),
            salt.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def log_result(self, test_name, success, message="", details=None):
        """记录测试结果"""
        result = {
            'test': test_name,
            'success': success,
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        
        if details and not success:
            print(f"   详情: {details}")
    
    def test_vps_connection(self):
        """测试VPS连接"""
        print("\n🔍 测试VPS连接...")
        
        try:
            response = requests.get(f"{self.vps_url}/", timeout=10)
            if response.status_code == 200:
                self.log_result("VPS连接", True, f"连接成功 ({response.status_code})")
            else:
                self.log_result("VPS连接", False, f"HTTP状态码: {response.status_code}")
        except requests.exceptions.ConnectionError:
            self.log_result("VPS连接", False, "无法连接到服务器", self.vps_url)
        except requests.exceptions.Timeout:
            self.log_result("VPS连接", False, "连接超时")
        except Exception as e:
            self.log_result("VPS连接", False, "连接异常", str(e))
    
    def test_api_status(self):
        """测试API状态接口"""
        print("\n🔍 测试API状态接口...")
        
        try:
            response = requests.get(f"{self.vps_url}/api/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'status' in data and data['status'] == 'running':
                    self.log_result("API状态", True, "API服务正常运行")
                else:
                    self.log_result("API状态", False, "API状态异常", data)
            else:
                self.log_result("API状态", False, f"HTTP状态码: {response.status_code}")
        except Exception as e:
            self.log_result("API状态", False, "API状态检查失败", str(e))
    
    def test_admin_login(self):
        """测试管理后台登录"""
        print("\n🔍 测试管理后台...")
        
        try:
            # 测试登录页面
            response = requests.get(f"{self.vps_url}/admin", timeout=10)
            if response.status_code == 200:
                self.log_result("管理后台", True, "管理后台页面可访问")
            else:
                self.log_result("管理后台", False, f"HTTP状态码: {response.status_code}")
        except Exception as e:
            self.log_result("管理后台", False, "管理后台访问失败", str(e))
    
    def test_frontend_page(self):
        """测试前端页面"""
        print("\n🔍 测试前端页面...")
        
        try:
            response = requests.get(f"{self.vps_url}/", timeout=10)
            if response.status_code == 200 and 'html' in response.headers.get('content-type', ''):
                self.log_result("前端页面", True, "前端页面正常")
            else:
                self.log_result("前端页面", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_result("前端页面", False, "前端页面访问异常", str(e))
    
    def test_database_connection(self):
        """测试数据库连接（仅在本地运行时）"""
        print("\n🔍 测试数据库连接...")
        
        db_paths = [
            "/var/lib/musicqr/musicqr.db",
            "./musicqr.db",
            "../server/musicqr.db"
        ]
        
        db_path = None
        for path in db_paths:
            if os.path.exists(path):
                db_path = path
                break
        
        if not db_path:
            self.log_result("数据库连接", False, "数据库文件不存在")
            return
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM auth_codes")
            count = cursor.fetchone()[0]
            self.log_result("数据库连接", True, f"数据库包含 {count} 个授权码")
            
            conn.close()
            
        except Exception as e:
            self.log_result("数据库连接", False, "数据库连接异常", str(e))
    
    def test_performance(self):
        """测试系统性能"""
        print("\n🔍 测试系统性能...")
        
        response_times = []
        
        # 进行10次API状态请求
        for i in range(10):
            try:
                start_time = time.time()
                response = requests.get(f"{self.vps_url}/api/status", timeout=10)
                end_time = time.time()
                
                if response.status_code == 200:
                    response_times.append(end_time - start_time)
                
            except Exception:
                pass
        
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            
            if avg_time < 1.0:  # 平均响应时间小于1秒
                self.log_result("性能测试", True, 
                              f"平均响应时间: {avg_time:.3f}s (最小: {min_time:.3f}s, 最大: {max_time:.3f}s)")
            else:
                self.log_result("性能测试", False, 
                              f"响应时间过长: {avg_time:.3f}s")
        else:
            self.log_result("性能测试", False, "无法获取响应时间数据")
    
    def test_ssl_certificate(self):
        """测试SSL证书"""
        print("\n🔍 测试SSL证书...")
        
        if not self.vps_url.startswith('https://'):
            self.log_result("SSL证书", False, "未使用HTTPS")
            return
        
        try:
            response = requests.get(self.vps_url, timeout=10, verify=True)
            if response.status_code == 200:
                self.log_result("SSL证书", True, "SSL证书有效")
            else:
                self.log_result("SSL证书", False, f"HTTPS访问失败: {response.status_code}")
        except requests.exceptions.SSLError as e:
            self.log_result("SSL证书", False, "SSL证书无效", str(e))
        except Exception as e:
            self.log_result("SSL证书", False, "SSL测试异常", str(e))
    
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "="*60)
        print("📊 测试报告")
        print("="*60)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests}")
        print(f"失败: {failed_tests}")
        print(f"成功率: {passed_tests/total_tests*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ 失败的测试:")
            for result in self.results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['message']}")
                    if result['details']:
                        print(f"    详情: {result['details']}")
        
        # 保存详细报告
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': {
                    'total': total_tests,
                    'passed': passed_tests,
                    'failed': failed_tests,
                    'success_rate': passed_tests/total_tests*100
                },
                'results': self.results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 详细报告已保存到: {report_file}")
        
        return failed_tests == 0
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始系统测试...")
        print(f"🎯 目标服务器: {self.vps_url}")
        
        # 执行所有测试
        self.test_vps_connection()
        self.test_api_status()
        self.test_admin_login()
        self.test_frontend_page()
        self.test_database_connection()
        self.test_performance()
        self.test_ssl_certificate()
        
        # 生成报告
        success = self.generate_report()
        
        if success:
            print("\n🎉 所有测试通过！系统运行正常。")
        else:
            print("\n⚠️ 部分测试失败，请检查系统配置。")
        
        return success

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='乐谱二维码验证系统测试脚本')
    parser.add_argument('--url', default='http://localhost:5000', 
                       help='VPS服务器地址 (默认: http://localhost:5000)')
    parser.add_argument('--api-key', help='API密钥')
    parser.add_argument('--production', action='store_true', 
                       help='生产环境测试 (使用 https://verify.yuzeguitar.me)')
    parser.add_argument('--admin', action='store_true',
                       help='测试管理后台功能')
    
    args = parser.parse_args()
    
    # 确定测试URL
    if args.production:
        vps_url = 'https://verify.yuzeguitar.me'
    else:
        vps_url = args.url
    
    # 创建测试器
    tester = SystemTester(vps_url=vps_url, api_key=args.api_key)
    
    # 运行测试
    success = tester.run_all_tests()
    
    # 退出码
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()

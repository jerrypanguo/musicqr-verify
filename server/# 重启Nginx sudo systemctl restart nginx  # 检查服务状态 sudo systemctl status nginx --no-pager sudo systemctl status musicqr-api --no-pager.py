#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
乐谱二维码验证系统 - VPS后端API
功能：授权码管理、验证服务、状态跟踪
"""

from flask import Flask, request, jsonify, render_template_string, render_template, redirect, url_for, session, flash, Response
from flask_cors import CORS
import sqlite3
import hashlib
import hmac
import json
from datetime import datetime
import os
import logging
from typing import Dict, List, Optional, Tuple
import ipaddress
import secrets
import string
import csv
import io

# 导入配置和模型
from config import Config
from models import init_db, AuthCode

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('musicqr_api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 创建Flask应用
# 检查模板目录是否存在
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
if not os.path.exists(template_dir):
    os.makedirs(template_dir, exist_ok=True)

app = Flask(__name__, template_folder='templates')
app.config.from_object(Config)
CORS(app)  # 允许跨域请求

# 管理后台配置
app.config['ADMIN_USERNAME'] = os.environ.get('ADMIN_USERNAME', 'admin')
app.config['ADMIN_PASSWORD'] = os.environ.get('ADMIN_PASSWORD', 'musicqr2024')

# 初始化数据库
init_db()

class AuthCodeManager:
    """授权码管理器"""
    
    def __init__(self):
        self.db_path = Config.DATABASE_PATH
    
    def get_db_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def verify_api_key(self, api_key: str) -> bool:
        """验证API密钥"""
        if not api_key:
            return False

        # 生成预期的API密钥
        expected = hmac.new(
            Config.SECRET_KEY.encode(),
            Config.API_KEY_SALT.encode(),
            hashlib.sha256
        ).hexdigest()

        # 直接比较提供的API密钥和预期的API密钥
        return hmac.compare_digest(expected, api_key)
    
    def sync_codes(self, codes_data: List[Dict], api_key: str) -> Tuple[bool, str, Dict]:
        """
        同步授权码到数据库
        
        Args:
            codes_data: 授权码数据列表
            api_key: API密钥
            
        Returns:
            Tuple[bool, str, Dict]: (成功状态, 消息, 统计信息)
        """
        # 验证API密钥
        if not self.verify_api_key(api_key):
            return False, "API密钥无效", {}
        
        if not codes_data:
            return False, "没有提供授权码数据", {}
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        added_count = 0
        skipped_count = 0
        error_count = 0
        
        try:
            for code_info in codes_data:
                code = code_info.get('code', '').strip().upper()
                created_date = code_info.get('created_date')
                
                if not code or len(code) != 12:
                    error_count += 1
                    continue
                
                # 检查是否已存在
                cursor.execute("SELECT id FROM auth_codes WHERE code = ?", (code,))
                if cursor.fetchone():
                    skipped_count += 1
                    continue
                
                # 插入新授权码
                cursor.execute("""
                    INSERT INTO auth_codes (code, created_date, activated, query_count)
                    VALUES (?, ?, FALSE, 0)
                """, (code, created_date or datetime.now().isoformat()))
                
                added_count += 1
            
            conn.commit()
            
            stats = {
                'added': added_count,
                'skipped': skipped_count,
                'errors': error_count,
                'total': len(codes_data)
            }
            
            logger.info(f"同步授权码完成: {stats}")
            return True, f"成功同步 {added_count} 个授权码", stats
            
        except Exception as e:
            conn.rollback()
            logger.error(f"同步授权码失败: {e}")
            return False, f"数据库错误: {str(e)}", {}
        
        finally:
            conn.close()
    
    def verify_code(self, code: str, client_ip: str = None, user_agent: str = None) -> Tuple[bool, Dict]:
        """
        验证授权码
        
        Args:
            code: 授权码
            client_ip: 客户端IP
            user_agent: 用户代理
            
        Returns:
            Tuple[bool, Dict]: (验证结果, 详细信息)
        """
        if not code or len(code.strip()) != 12:
            return False, {
                'valid': False,
                'message': '授权码格式无效',
                'activated': False
            }
        
        code = code.strip().upper()
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 查询授权码
            cursor.execute("""
                SELECT id, code, activated, activation_date, query_count
                FROM auth_codes WHERE code = ?
            """, (code,))
            
            result = cursor.fetchone()
            
            if not result:
                return False, {
                    'valid': False,
                    'message': '授权码不存在或无效',
                    'activated': False
                }
            
            # 更新查询统计
            new_query_count = result['query_count'] + 1
            now = datetime.now().isoformat()
            
            # 如果是首次激活
            if not result['activated']:
                cursor.execute("""
                    UPDATE auth_codes 
                    SET activated = TRUE, 
                        activation_date = ?, 
                        activation_ip = ?, 
                        activation_user_agent = ?,
                        query_count = ?,
                        last_query_date = ?
                    WHERE id = ?
                """, (now, client_ip, user_agent, new_query_count, now, result['id']))
                
                conn.commit()
                
                logger.info(f"授权码首次激活: {code} from {client_ip}")
                
                return True, {
                    'valid': True,
                    'activated': True,
                    'activation_date': now,
                    'message': '验证成功！这是正版乐谱',
                    'first_activation': True
                }
            else:
                # 更新查询记录
                cursor.execute("""
                    UPDATE auth_codes 
                    SET query_count = ?, last_query_date = ?
                    WHERE id = ?
                """, (new_query_count, now, result['id']))
                
                conn.commit()
                
                return True, {
                    'valid': True,
                    'activated': True,
                    'activation_date': result['activation_date'],
                    'message': '验证成功！这是正版乐谱',
                    'first_activation': False
                }
                
        except Exception as e:
            logger.error(f"验证授权码失败: {e}")
            return False, {
                'valid': False,
                'message': '服务器错误，请稍后重试',
                'activated': False
            }
        
        finally:
            conn.close()
    
    def get_stats(self) -> Dict:
        """获取系统统计信息"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 总授权码数量
            cursor.execute("SELECT COUNT(*) as total FROM auth_codes")
            total = cursor.fetchone()['total']
            
            # 已激活数量
            cursor.execute("SELECT COUNT(*) as activated FROM auth_codes WHERE activated = TRUE")
            activated = cursor.fetchone()['activated']
            
            # 今日查询数量
            today = datetime.now().date().isoformat()
            cursor.execute("""
                SELECT COUNT(*) as today_queries 
                FROM auth_codes 
                WHERE DATE(last_query_date) = ?
            """, (today,))
            today_queries = cursor.fetchone()['today_queries']
            
            return {
                'total_codes': total,
                'activated_codes': activated,
                'activation_rate': round(activated / total * 100, 2) if total > 0 else 0,
                'today_queries': today_queries
            }
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
        
        finally:
            conn.close()

# 创建授权码管理器实例
auth_manager = AuthCodeManager()

def get_client_ip() -> str:
    """获取客户端真实IP"""
    # 检查代理头
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr

@app.route('/')
def index():
    """首页 - 显示系统状态"""
    stats = auth_manager.get_stats()
    
    html_template = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>乐谱验证系统 - API服务</title>
        <style>
            body { font-family: Georgia, serif; margin: 40px; background: #f8f8f8; }
            .container { max-width: 600px; margin: 0 auto; background: white; padding: 40px; border: 1px solid #ddd; }
            h1 { color: #333; text-align: center; margin-bottom: 30px; }
            .stats { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 30px 0; }
            .stat-item { text-align: center; padding: 20px; background: #f8f8f8; border: 1px solid #eee; }
            .stat-number { font-size: 2em; font-weight: bold; color: #333; }
            .stat-label { color: #666; margin-top: 5px; }
            .api-info { margin-top: 30px; padding: 20px; background: #f0f0f0; border-left: 4px solid #333; }
            .footer { text-align: center; margin-top: 30px; color: #666; font-size: 0.9em; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎵 乐谱验证系统</h1>
            <p style="text-align: center; color: #666;">API服务运行中</p>
            
            <div class="stats">
                <div class="stat-item">
                    <div class="stat-number">{{ stats.total_codes or 0 }}</div>
                    <div class="stat-label">总授权码</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{{ stats.activated_codes or 0 }}</div>
                    <div class="stat-label">已激活</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{{ stats.activation_rate or 0 }}%</div>
                    <div class="stat-label">激活率</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{{ stats.today_queries or 0 }}</div>
                    <div class="stat-label">今日查询</div>
                </div>
            </div>
            
            <div class="api-info">
                <h3>API端点</h3>
                <p><strong>验证授权码:</strong> GET /api/verify/{code}</p>
                <p><strong>同步授权码:</strong> POST /api/sync-codes</p>
                <p><strong>系统状态:</strong> GET /api/status</p>
            </div>
            
            <div class="footer">
                <p>乐谱验证系统 v2.0 - Yuze Pan</p>
                <p>服务时间: {{ current_time }}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(html_template, 
                                stats=stats, 
                                current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@app.route('/api/verify/<code>')
def verify_code_api(code):
    """验证授权码API"""
    client_ip = get_client_ip()
    user_agent = request.headers.get('User-Agent', '')
    
    success, result = auth_manager.verify_code(code, client_ip, user_agent)
    
    if success:
        return jsonify(result), 200
    else:
        return jsonify(result), 400

@app.route('/api/sync-codes', methods=['POST'])
def sync_codes_api():
    """同步授权码API"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400
        
        codes_data = data.get('codes', [])
        api_key = data.get('api_key', '')
        
        success, message, stats = auth_manager.sync_codes(codes_data, api_key)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'stats': stats
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 400
            
    except Exception as e:
        logger.error(f"同步API错误: {e}")
        return jsonify({'error': '服务器内部错误'}), 500

@app.route('/api/status')
def status_api():
    """系统状态API"""
    stats = auth_manager.get_stats()
    return jsonify({
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'stats': stats
    })

@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return jsonify({'error': '接口不存在'}), 404

# ==================== 管理后台路由 ====================

def admin_required(f):
    """管理员登录装饰器"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
def admin_redirect():
    """管理后台重定向"""
    return redirect(url_for('admin_login'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """管理员登录"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if (username == app.config['ADMIN_USERNAME'] and
            password == app.config['ADMIN_PASSWORD']):
            session['admin_logged_in'] = True
            session['admin_username'] = username
            flash('登录成功！', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('用户名或密码错误', 'error')

    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    """管理员退出"""
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    flash('已安全退出', 'info')
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """管理仪表板"""
    stats = auth_manager.get_stats()

    # 获取最近激活的授权码
    conn = auth_manager.get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT code, activation_date, query_count
            FROM auth_codes
            WHERE activated = TRUE
            ORDER BY activation_date DESC
            LIMIT 10
        """)
        recent_activations = [dict(row) for row in cursor.fetchall()]

        # 获取7天激活趋势
        cursor.execute("""
            SELECT DATE(activation_date) as date, COUNT(*) as count
            FROM auth_codes
            WHERE activated = TRUE
            AND activation_date >= DATE('now', '-7 days')
            GROUP BY DATE(activation_date)
            ORDER BY date
        """)
        daily_stats = [dict(row) for row in cursor.fetchall()]
        max_daily_count = max([d['count'] for d in daily_stats]) if daily_stats else 0

        # 数据库大小
        db_size_mb = os.path.getsize(auth_manager.db_path) / (1024 * 1024) if os.path.exists(auth_manager.db_path) else 0

    except Exception as e:
        logger.error(f"获取仪表板数据失败: {e}")
        recent_activations = []
        daily_stats = []
        max_daily_count = 0
        db_size_mb = 0
    finally:
        conn.close()

    return render_template('admin_dashboard.html',
                         stats=stats,
                         recent_activations=recent_activations,
                         daily_stats=daily_stats,
                         max_daily_count=max_daily_count,
                         db_size_mb=db_size_mb,
                         current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@app.route('/admin/codes')
@admin_required
def admin_codes():
    """授权码管理"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '')
    sort = request.args.get('sort', 'created_desc')

    conn = auth_manager.get_db_connection()
    cursor = conn.cursor()

    try:
        # 构建查询条件
        where_conditions = []
        params = []

        if search:
            where_conditions.append("code LIKE ?")
            params.append(f"%{search.upper()}%")

        if status == 'activated':
            where_conditions.append("activated = TRUE")
        elif status == 'not_activated':
            where_conditions.append("activated = FALSE")

        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""

        # 排序
        sort_mapping = {
            'created_desc': 'created_date DESC',
            'created_asc': 'created_date ASC',
            'activation_desc': 'activation_date DESC',
            'query_desc': 'query_count DESC'
        }
        order_clause = f" ORDER BY {sort_mapping.get(sort, 'created_date DESC')}"

        # 获取总数
        cursor.execute(f"SELECT COUNT(*) FROM auth_codes{where_clause}", params)
        total_count = cursor.fetchone()[0]

        # 获取已激活数量
        activated_params = params.copy()
        activated_where = where_conditions.copy()
        activated_where.append("activated = TRUE")
        activated_where_clause = " WHERE " + " AND ".join(activated_where)
        cursor.execute(f"SELECT COUNT(*) FROM auth_codes{activated_where_clause}", activated_params)
        activated_count = cursor.fetchone()[0]

        # 分页查询
        offset = (page - 1) * per_page
        cursor.execute(f"""
            SELECT * FROM auth_codes{where_clause}{order_clause}
            LIMIT ? OFFSET ?
        """, params + [per_page, offset])

        codes = [dict(row) for row in cursor.fetchall()]

        # 简单分页对象
        class Pagination:
            def __init__(self, page, per_page, total):
                self.page = page
                self.per_page = per_page
                self.total = total
                self.pages = (total + per_page - 1) // per_page
                self.has_prev = page > 1
                self.has_next = page < self.pages
                self.prev_num = page - 1 if self.has_prev else None
                self.next_num = page + 1 if self.has_next else None

            def iter_pages(self):
                for num in range(max(1, self.page - 2), min(self.pages + 1, self.page + 3)):
                    yield num

        pagination = Pagination(page, per_page, total_count)

    except Exception as e:
        logger.error(f"获取授权码列表失败: {e}")
        codes = []
        pagination = None
        total_count = 0
        activated_count = 0
    finally:
        conn.close()

    return render_template('admin_codes.html',
                         codes=codes,
                         pagination=pagination,
                         total_count=total_count,
                         activated_count=activated_count)

@app.route('/admin/codes/add', methods=['GET', 'POST'])
@admin_required
def admin_add_code():
    """添加授权码"""
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'single':
            # 单个添加
            code = request.form.get('code', '').strip().upper()
            if not code:
                # 自动生成
                import secrets
                import string
                alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # 排除容易混淆的字符
                code = ''.join(secrets.choice(alphabet) for _ in range(12))

            if len(code) != 12:
                flash('授权码长度必须为12位', 'error')
            else:
                conn = auth_manager.get_db_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                        INSERT INTO auth_codes (code, created_date, activated, query_count)
                        VALUES (?, ?, FALSE, 0)
                    """, (code, datetime.now().isoformat()))
                    conn.commit()
                    flash(f'成功添加授权码: {code}', 'success')
                except sqlite3.IntegrityError:
                    flash(f'授权码 {code} 已存在', 'error')
                except Exception as e:
                    flash(f'添加失败: {str(e)}', 'error')
                finally:
                    conn.close()

        elif action == 'batch':
            # 批量添加
            count = int(request.form.get('count', 0))
            if count <= 0 or count > 1000:
                flash('生成数量必须在1-1000之间', 'error')
            else:
                conn = auth_manager.get_db_connection()
                cursor = conn.cursor()

                # 获取现有授权码以避免重复
                cursor.execute("SELECT code FROM auth_codes")
                existing_codes = {row[0] for row in cursor.fetchall()}

                import secrets
                import string
                alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'

                added_count = 0
                for _ in range(count):
                    # 生成唯一授权码
                    attempts = 0
                    while attempts < 100:  # 最多尝试100次
                        code = ''.join(secrets.choice(alphabet) for _ in range(12))
                        if code not in existing_codes:
                            break
                        attempts += 1

                    if attempts >= 100:
                        break

                    try:
                        cursor.execute("""
                            INSERT INTO auth_codes (code, created_date, activated, query_count)
                            VALUES (?, ?, FALSE, 0)
                        """, (code, datetime.now().isoformat()))
                        existing_codes.add(code)
                        added_count += 1
                    except Exception:
                        continue

                conn.commit()
                conn.close()
                flash(f'成功生成 {added_count} 个授权码', 'success')

        elif action == 'import':
            # 导入授权码
            import_text = request.form.get('import_text', '').strip()
            skip_duplicates = request.form.get('skip_duplicates') == 'on'

            if not import_text:
                flash('请输入要导入的授权码', 'error')
            else:
                lines = [line.strip() for line in import_text.split('\n') if line.strip()]
                conn = auth_manager.get_db_connection()
                cursor = conn.cursor()

                added_count = 0
                skipped_count = 0
                error_count = 0

                for line in lines:
                    if ',' in line:
                        # CSV格式
                        parts = line.split(',', 1)
                        code = parts[0].strip().upper()
                        created_date = parts[1].strip() if len(parts) > 1 else datetime.now().isoformat()
                    else:
                        # 纯文本格式
                        code = line.upper()
                        created_date = datetime.now().isoformat()

                    if len(code) != 12:
                        error_count += 1
                        continue

                    try:
                        cursor.execute("""
                            INSERT INTO auth_codes (code, created_date, activated, query_count)
                            VALUES (?, ?, FALSE, 0)
                        """, (code, created_date))
                        added_count += 1
                    except sqlite3.IntegrityError:
                        if skip_duplicates:
                            skipped_count += 1
                        else:
                            error_count += 1
                    except Exception:
                        error_count += 1

                conn.commit()
                conn.close()

                message = f'导入完成: 添加 {added_count} 个'
                if skipped_count > 0:
                    message += f', 跳过重复 {skipped_count} 个'
                if error_count > 0:
                    message += f', 错误 {error_count} 个'

                flash(message, 'success' if added_count > 0 else 'info')

    # 获取最近添加的授权码
    conn = auth_manager.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT * FROM auth_codes
            ORDER BY created_date DESC
            LIMIT 10
        """)
        recent_codes = [dict(row) for row in cursor.fetchall()]
    except Exception:
        recent_codes = []
    finally:
        conn.close()

    return render_template('admin_add_code.html', recent_codes=recent_codes)

@app.route('/admin/codes/<code>')
@admin_required
def admin_code_detail(code):
    """授权码详情"""
    conn = auth_manager.get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM auth_codes WHERE code = ?", (code,))
        code_info = cursor.fetchone()

        if not code_info:
            flash('授权码不存在', 'error')
            return redirect(url_for('admin_codes'))

        code_info = dict(code_info)

    except Exception as e:
        flash(f'获取授权码信息失败: {str(e)}', 'error')
        return redirect(url_for('admin_codes'))
    finally:
        conn.close()

    return render_template('admin_code_detail.html', code_info=code_info)

@app.route('/admin/codes/<code>/delete')
@admin_required
def admin_delete_code(code):
    """删除授权码"""
    conn = auth_manager.get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM auth_codes WHERE code = ?", (code,))
        if cursor.rowcount > 0:
            conn.commit()
            flash(f'成功删除授权码: {code}', 'success')
        else:
            flash('授权码不存在', 'error')
    except Exception as e:
        flash(f'删除失败: {str(e)}', 'error')
    finally:
        conn.close()

    return redirect(url_for('admin_codes'))



@app.route('/admin/export')
@admin_required
def admin_export():
    """导出数据"""
    codes_param = request.args.get('codes')

    conn = auth_manager.get_db_connection()
    cursor = conn.cursor()

    try:
        if codes_param:
            codes_list = codes_param.split(',')
            placeholders = ','.join(['?' for _ in codes_list])
            cursor.execute(f"SELECT * FROM auth_codes WHERE code IN ({placeholders})", codes_list)
        else:
            cursor.execute("SELECT * FROM auth_codes ORDER BY created_date DESC")

        codes = cursor.fetchall()

        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(['授权码', '创建时间', '是否激活', '激活时间', '查询次数'])

        for code in codes:
            writer.writerow([
                code[1],  # code
                code[2],  # created_date
                '是' if code[3] else '否',  # activated
                code[4] or '',  # activation_date
                code[7] or 0   # query_count
            ])

        output.seek(0)

        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=auth_codes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            }
        )

    except Exception as e:
        flash(f'导出失败: {str(e)}', 'error')
        return redirect(url_for('admin_codes'))
    finally:
        conn.close()

@app.route('/admin/system-info')
@admin_required
def admin_system_info():
    """系统信息"""
    try:
        import psutil
        import platform

        system_info = {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total // (1024**3),  # GB
            'memory_used': round(psutil.virtual_memory().percent, 1),
            'disk_total': psutil.disk_usage('/').total // (1024**3),  # GB
            'disk_used': round(psutil.disk_usage('/').percent, 1),
            'uptime': str(datetime.now() - datetime.fromtimestamp(psutil.boot_time())).split('.')[0],
        }
    except ImportError:
        # 如果psutil不可用，使用基本信息
        import platform
        system_info = {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'cpu_count': 'Unknown',
            'memory_total': 'Unknown',
            'memory_used': 'Unknown',
            'disk_total': 'Unknown',
            'disk_used': 'Unknown',
            'uptime': 'Unknown',
        }
    except Exception as e:
        logger.error(f"获取系统信息失败: {e}")
        system_info = {
            'platform': 'Unknown',
            'python_version': 'Unknown',
            'cpu_count': 'Unknown',
            'memory_total': 'Unknown',
            'memory_used': 'Unknown',
            'disk_total': 'Unknown',
            'disk_used': 'Unknown',
            'uptime': 'Unknown',
        }

    # 数据库信息
    db_info = {
        'path': auth_manager.db_path,
        'size_mb': os.path.getsize(auth_manager.db_path) / (1024**2) if os.path.exists(auth_manager.db_path) else 0,
        'exists': os.path.exists(auth_manager.db_path)
    }

    return render_template('admin_system_info.html',
                         system_info=system_info,
                         db_info=db_info,
                         current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))





@app.route('/admin/bulk-action', methods=['POST'])
@admin_required
def admin_bulk_action():
    """批量操作"""
    action = request.form.get('action')
    selected_codes = request.form.getlist('selected_codes')

    if not selected_codes:
        flash('请选择要操作的授权码', 'error')
        return redirect(url_for('admin_codes'))

    if action == 'delete':
        conn = auth_manager.get_db_connection()
        cursor = conn.cursor()

        try:
            placeholders = ','.join(['?' for _ in selected_codes])
            cursor.execute(f"DELETE FROM auth_codes WHERE code IN ({placeholders})", selected_codes)
            deleted_count = cursor.rowcount
            conn.commit()
            flash(f'成功删除 {deleted_count} 个授权码', 'success')
        except Exception as e:
            flash(f'批量删除失败: {str(e)}', 'error')
        finally:
            conn.close()

    elif action == 'export':
        # 导出选中的授权码
        return redirect(url_for('admin_export', codes=','.join(selected_codes)))

    return redirect(url_for('admin_codes'))





@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    logger.error(f"服务器内部错误: {error}")
    return jsonify({'error': '服务器内部错误'}), 500

if __name__ == '__main__':
    # 开发环境运行
    app.run(host='0.0.0.0', port=5000, debug=False)

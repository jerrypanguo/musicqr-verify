# 乐谱验证系统 - API接口文档

## 🎯 API概述

乐谱验证系统提供RESTful API接口，支持授权码验证、状态查询、数据同步等功能。

### 基础信息
- **Base URL**: `https://verify.yuzeguitar.me`
- **协议**: HTTPS
- **数据格式**: JSON
- **字符编码**: UTF-8

### 认证方式
- **公开接口**: 无需认证（验证接口）
- **管理接口**: 需要API密钥认证
- **管理后台**: 需要会话认证

## 🔐 认证机制

### API密钥生成
```python
import hashlib
import hmac

secret_key = "your-secret-key"
salt = "musicqr_api_salt_2024"
api_key = hmac.new(secret_key.encode(), salt.encode(), hashlib.sha256).hexdigest()
```

### 请求头设置
```http
Content-Type: application/json
X-API-Key: your-generated-api-key
```

## 📋 公开接口

### 1. 系统状态查询

#### 接口信息
- **URL**: `/api/status`
- **方法**: `GET`
- **认证**: 无需认证
- **描述**: 获取系统运行状态和基础统计

#### 请求示例
```bash
curl -X GET https://verify.yuzeguitar.me/api/status
```

#### 响应示例
```json
{
  "status": "running",
  "timestamp": "2024-08-08T12:00:00Z",
  "version": "2.0.0",
  "stats": {
    "total_codes": 1250,
    "activated_codes": 856,
    "activation_rate": 68.5,
    "today_queries": 42
  }
}
```

#### 响应字段说明
| 字段 | 类型 | 说明 |
|------|------|------|
| status | string | 系统状态 (running/maintenance) |
| timestamp | string | 响应时间戳 (ISO 8601) |
| version | string | 系统版本号 |
| stats.total_codes | integer | 总授权码数量 |
| stats.activated_codes | integer | 已激活授权码数量 |
| stats.activation_rate | float | 激活率百分比 |
| stats.today_queries | integer | 今日查询次数 |

### 2. 授权码验证

#### 接口信息
- **URL**: `/api/verify/{code}`
- **方法**: `GET`
- **认证**: 无需认证
- **描述**: 验证授权码有效性并记录查询

#### 请求示例
```bash
curl -X GET https://verify.yuzeguitar.me/api/verify/ABCD12345678
```

#### 响应示例（有效授权码）
```json
{
  "valid": true,
  "activated": true,
  "code": "ABCD12345678",
  "message": "正版乐谱，验证通过",
  "activation_date": "2024-08-01T10:30:00Z",
  "query_count": 15,
  "timestamp": "2024-08-08T12:00:00Z"
}
```

#### 响应示例（无效授权码）
```json
{
  "valid": false,
  "activated": false,
  "code": "INVALID12345",
  "message": "授权码不存在或无效",
  "timestamp": "2024-08-08T12:00:00Z"
}
```

#### 响应字段说明
| 字段 | 类型 | 说明 |
|------|------|------|
| valid | boolean | 授权码是否有效 |
| activated | boolean | 是否已激活 |
| code | string | 授权码 |
| message | string | 验证结果消息 |
| activation_date | string | 激活时间 (仅已激活时返回) |
| query_count | integer | 查询次数 (仅已激活时返回) |
| timestamp | string | 响应时间戳 |

## 🔒 管理接口

### 1. 同步授权码

#### 接口信息
- **URL**: `/api/sync-codes`
- **方法**: `POST`
- **认证**: 需要API密钥
- **描述**: 从客户端同步授权码到服务器

#### 请求头
```http
Content-Type: application/json
X-API-Key: your-api-key
```

#### 请求体示例
```json
{
  "codes": [
    {
      "code": "ABCD12345678",
      "created_date": "2024-08-08T12:00:00Z"
    },
    {
      "code": "EFGH87654321",
      "created_date": "2024-08-08T12:01:00Z"
    }
  ]
}
```

#### 响应示例
```json
{
  "success": true,
  "message": "授权码同步成功",
  "synced_count": 2,
  "skipped_count": 0,
  "details": {
    "new_codes": ["ABCD12345678", "EFGH87654321"],
    "existing_codes": []
  },
  "timestamp": "2024-08-08T12:00:00Z"
}
```

#### 错误响应示例
```json
{
  "success": false,
  "message": "API密钥无效",
  "error_code": "INVALID_API_KEY",
  "timestamp": "2024-08-08T12:00:00Z"
}
```

### 2. 批量查询授权码

#### 接口信息
- **URL**: `/api/codes/batch`
- **方法**: `POST`
- **认证**: 需要API密钥
- **描述**: 批量查询多个授权码状态

#### 请求体示例
```json
{
  "codes": ["ABCD12345678", "EFGH87654321", "IJKL13579246"]
}
```

#### 响应示例
```json
{
  "success": true,
  "results": [
    {
      "code": "ABCD12345678",
      "valid": true,
      "activated": true,
      "activation_date": "2024-08-01T10:30:00Z",
      "query_count": 15
    },
    {
      "code": "EFGH87654321",
      "valid": true,
      "activated": false,
      "activation_date": null,
      "query_count": 0
    },
    {
      "code": "IJKL13579246",
      "valid": false,
      "activated": false,
      "activation_date": null,
      "query_count": 0
    }
  ],
  "timestamp": "2024-08-08T12:00:00Z"
}
```

## 🛡️ 管理后台接口

### 1. 管理员登录

#### 接口信息
- **URL**: `/admin/login`
- **方法**: `POST`
- **认证**: 用户名密码
- **描述**: 管理员登录获取会话

#### 请求体示例
```json
{
  "username": "admin",
  "password": "your-password"
}
```

#### 响应示例
```json
{
  "success": true,
  "message": "登录成功",
  "redirect_url": "/admin/dashboard"
}
```

### 2. 获取授权码列表

#### 接口信息
- **URL**: `/admin/api/codes`
- **方法**: `GET`
- **认证**: 需要管理员会话
- **描述**: 获取授权码列表（支持分页和筛选）

#### 查询参数
| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| page | integer | 页码 | 1 |
| per_page | integer | 每页数量 | 20 |
| search | string | 搜索关键词 | - |
| status | string | 状态筛选 (all/activated/unactivated) | all |
| sort | string | 排序字段 | created_date |
| order | string | 排序方向 (asc/desc) | desc |

#### 请求示例
```bash
curl -X GET "https://verify.yuzeguitar.me/admin/api/codes?page=1&per_page=20&status=activated" \
  -H "Cookie: session=your-session-cookie"
```

#### 响应示例
```json
{
  "success": true,
  "data": {
    "codes": [
      {
        "code": "ABCD12345678",
        "created_date": "2024-08-01T10:00:00Z",
        "activated": true,
        "activation_date": "2024-08-01T10:30:00Z",
        "activation_ip": "192.168.1.100",
        "query_count": 15,
        "last_query_date": "2024-08-08T11:45:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total": 856,
      "pages": 43
    }
  }
}
```

## 📊 错误代码

### HTTP状态码
| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 401 | 未授权（API密钥无效） |
| 403 | 禁止访问（权限不足） |
| 404 | 资源不存在 |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |

### 业务错误代码
| 错误代码 | 说明 |
|----------|------|
| INVALID_API_KEY | API密钥无效 |
| INVALID_CODE_FORMAT | 授权码格式错误 |
| CODE_NOT_FOUND | 授权码不存在 |
| DUPLICATE_CODE | 授权码重复 |
| DATABASE_ERROR | 数据库操作错误 |
| RATE_LIMIT_EXCEEDED | 请求频率超限 |

## 🔧 SDK示例

### Python SDK示例

```python
import requests
import hashlib
import hmac

class MusicQRClient:
    def __init__(self, base_url, secret_key):
        self.base_url = base_url.rstrip('/')
        self.api_key = self._generate_api_key(secret_key)
    
    def _generate_api_key(self, secret_key):
        salt = "musicqr_api_salt_2024"
        return hmac.new(
            secret_key.encode(),
            salt.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def _get_headers(self):
        return {
            'Content-Type': 'application/json',
            'X-API-Key': self.api_key
        }
    
    def get_status(self):
        """获取系统状态"""
        response = requests.get(f"{self.base_url}/api/status")
        return response.json()
    
    def verify_code(self, code):
        """验证授权码"""
        response = requests.get(f"{self.base_url}/api/verify/{code}")
        return response.json()
    
    def sync_codes(self, codes):
        """同步授权码"""
        data = {'codes': codes}
        response = requests.post(
            f"{self.base_url}/api/sync-codes",
            json=data,
            headers=self._get_headers()
        )
        return response.json()

# 使用示例
client = MusicQRClient(
    base_url='https://verify.yuzeguitar.me',
    secret_key='your-secret-key'
)

# 获取系统状态
status = client.get_status()
print(f"系统状态: {status['status']}")

# 验证授权码
result = client.verify_code('ABCD12345678')
print(f"验证结果: {result['message']}")

# 同步授权码
codes = [
    {'code': 'ABCD12345678', 'created_date': '2024-08-08T12:00:00Z'}
]
sync_result = client.sync_codes(codes)
print(f"同步结果: {sync_result['message']}")
```

### JavaScript SDK示例

```javascript
class MusicQRClient {
    constructor(baseUrl, secretKey) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.apiKey = this.generateApiKey(secretKey);
    }
    
    async generateApiKey(secretKey) {
        const salt = 'musicqr_api_salt_2024';
        const encoder = new TextEncoder();
        const key = await crypto.subtle.importKey(
            'raw',
            encoder.encode(secretKey),
            { name: 'HMAC', hash: 'SHA-256' },
            false,
            ['sign']
        );
        const signature = await crypto.subtle.sign(
            'HMAC',
            key,
            encoder.encode(salt)
        );
        return Array.from(new Uint8Array(signature))
            .map(b => b.toString(16).padStart(2, '0'))
            .join('');
    }
    
    getHeaders() {
        return {
            'Content-Type': 'application/json',
            'X-API-Key': this.apiKey
        };
    }
    
    async getStatus() {
        const response = await fetch(`${this.baseUrl}/api/status`);
        return response.json();
    }
    
    async verifyCode(code) {
        const response = await fetch(`${this.baseUrl}/api/verify/${code}`);
        return response.json();
    }
    
    async syncCodes(codes) {
        const response = await fetch(`${this.baseUrl}/api/sync-codes`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify({ codes })
        });
        return response.json();
    }
}

// 使用示例
const client = new MusicQRClient(
    'https://verify.yuzeguitar.me',
    'your-secret-key'
);

// 验证授权码
client.verifyCode('ABCD12345678').then(result => {
    console.log('验证结果:', result.message);
});
```

## 📞 技术支持

如有API使用问题，请联系：
- **开发者**: Yuze Pan
- **微信**: Guitar_yuze
- **版本**: v2.0.0

---

**API文档持续更新中，请关注最新版本** 🔄

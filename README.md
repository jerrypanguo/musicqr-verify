# 乐谱二维码验证系统 - VPS版本

## 🎯 项目简介

乐谱二维码验证系统VPS版本是一个基于云服务器的正版乐谱验证解决方案。用户扫描二维码后，系统会实时验证授权码的有效性，并记录激活状态。

### ✨ 主要特性

- 🔄 **分布式架构**: 本地客户端 + VPS服务器 + 前端页面
- 🔐 **实时验证**: 基于VPS的在线验证服务
- 📊 **状态管理**: 自动记录激活时间和使用统计
- 🎨 **极简设计**: 黑白风格，优雅美观
- 🛡️ **安全可靠**: HTTPS加密和API密钥认证
- 📱 **管理后台**: 完整的Web管理界面
- 📈 **数据统计**: 详细的使用数据和分析

### 🏗️ 系统架构

```
本地Python客户端 → VPS API服务器 → 用户验证页面
     ↓                    ↓              ↓
  生成授权码           管理状态        实时验证
  同步到VPS           记录激活        优雅界面
```

## 📁 项目结构

```
乐谱验证系统-VPS版/
├── README.md                    # 项目说明
├── 部署指南.md                  # 完整部署指南
├── 使用说明.md                  # 用户使用说明
├── 迁移指南.md                  # 服务器迁移指南
├── 
├── client/                      # 本地客户端
│   ├── generate_codes.py        # 主程序 - 生成授权码
│   ├── config.py               # 客户端配置
│   ├── requirements.txt        # Python依赖
│   ├── fonts/                  # 字体文件
│   │   ├── Bodoni 72.ttc      # 主要字体
│   │   └── README.md          # 字体说明
│   ├── output/                 # 输出目录
│   └── data/                   # 数据目录
│
├── server/                      # VPS服务器端
│   ├── app.py                  # Flask主应用
│   ├── models.py               # 数据库模型
│   ├── config.py               # 服务器配置
│   ├── requirements.txt        # Python依赖
│   ├── templates/              # HTML模板
│   │   ├── base.html          # 基础模板
│   │   ├── admin_login.html   # 登录页面
│   │   ├── admin_dashboard.html # 仪表板
│   │   ├── admin_codes.html   # 授权码管理
│   │   ├── admin_add_code.html # 添加授权码
│   │   ├── admin_code_detail.html # 授权码详情
│   │   └── admin_system_info.html # 系统信息
│   └── deploy/                 # 部署脚本
│       ├── setup.sh           # 一键部署脚本
│       ├── nginx.conf         # Nginx配置
│       ├── systemd.service    # 系统服务配置
│       ├── update.sh          # 更新脚本
│       └── backup.sh          # 备份脚本
│
├── web/                        # 前端页面
│   ├── index.html             # 验证页面
│   ├── style.css              # 样式文件
│   └── script.js              # JavaScript逻辑
│
├── docs/                       # 文档目录
│   ├── API文档.md             # API接口文档
│   ├── 数据库设计.md          # 数据库结构说明
│   ├── 安全说明.md            # 安全配置说明
│   └── 故障排除.md            # 常见问题解决
│
├── scripts/                    # 工具脚本
│   ├── test_system.py         # 系统测试脚本
│   ├── migrate_data.py        # 数据迁移脚本
│   └── backup_restore.py      # 备份恢复脚本
│
└── examples/                   # 示例文件
    ├── .env.example           # 环境变量示例
    ├── nginx.example.conf     # Nginx配置示例
    └── codes.example.json     # 授权码数据示例
```

## 🚀 快速开始

### 1. 环境要求

- **服务器**: Ubuntu 22.04 LTS
- **内存**: 最低1GB，推荐2GB
- **存储**: 最低10GB可用空间
- **域名**: 用于HTTPS访问（推荐）

### 2. 一键部署

```bash
# 下载项目
git clone https://github.com/your-repo/musicqr-vps.git
cd musicqr-vps

# 运行部署脚本
chmod +x server/deploy/setup.sh
sudo ./server/deploy/setup.sh
```

### 3. 访问系统

- **前端验证**: `https://your-domain.com/`
- **管理后台**: `https://your-domain.com/admin`
- **API接口**: `https://your-domain.com/api/status`

## 📖 详细文档

- [📋 部署指南](部署指南.md) - 完整的服务器部署说明
- [📱 使用说明](使用说明.md) - 用户和管理员使用指南
- [🔄 迁移指南](迁移指南.md) - 服务器迁移和数据备份
- [🔧 API文档](docs/API文档.md) - 接口详细说明
- [🛡️ 安全说明](docs/安全说明.md) - 安全配置指南

## 🔧 配置说明

### 客户端配置

```bash
# 设置环境变量
export VPS_URL='https://your-domain.com'
export CLIENT_SECRET_KEY='your-secret-key'
export API_KEY_SALT='musicqr_api_salt_2024'
```

### 服务器配置

```bash
# 编辑配置文件
sudo nano /var/www/musicqr/.env

# 添加配置
SECRET_KEY=your-secret-key
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-password
```

## 🧪 测试系统

```bash
# 运行系统测试
python3 scripts/test_system.py --url https://your-domain.com

# 测试管理后台
python3 scripts/test_system.py --admin
```

## 📊 功能特性

### 客户端功能
- ✅ 生成二维码PDF（横版/竖版）
- ✅ 自动同步到VPS服务器
- ✅ 批量生成授权码
- ✅ 优雅的字体支持

### 服务器功能
- ✅ 实时验证API
- ✅ 状态管理和统计
- ✅ 安全认证机制
- ✅ 自动备份功能

### 管理后台
- ✅ 仪表板和统计
- ✅ 授权码管理
- ✅ 批量操作
- ✅ 数据导出
- ✅ 系统监控

### 前端页面
- ✅ 实时验证
- ✅ 优雅界面
- ✅ 移动端支持
- ✅ 错误处理

## 🛡️ 安全特性

- 🔐 HTTPS加密通信
- 🔑 API密钥认证
- 🛡️ 会话管理
- 📝 操作日志记录
- 🚫 输入验证和过滤

## 📞 技术支持

- **开发者**: Yuze Pan
- **微信**: Guitar_yuze
- **版本**: v2.0.0
- **更新时间**: 2024年8月

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

**让正版乐谱验证变得简单而优雅** 🎵

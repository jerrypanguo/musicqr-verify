/**
 * 乐谱验证系统 - VPS版本 JavaScript
 * 功能：与VPS API通信，实现实时验证
 */

class BookVerifier {
    constructor() {
        this.apiBaseUrl = this.getApiBaseUrl();
        this.currentCode = null;
        this.retryCount = 0;
        this.maxRetries = 3;
        
        this.init();
    }
    
    /**
     * 获取API基础URL
     */
    getApiBaseUrl() {
        // 从当前域名推断API地址
        const currentHost = window.location.host;
        const currentProtocol = window.location.protocol;
        
        // 如果是本地开发环境
        if (currentHost.includes('localhost') || currentHost.includes('127.0.0.1')) {
            return 'http://localhost:5000';
        }
        
        // 生产环境使用当前域名
        return `${currentProtocol}//${currentHost}`;
    }
    
    /**
     * 初始化验证器
     */
    init() {
        console.log('🎵 乐谱验证系统初始化...');
        console.log('📡 API地址:', this.apiBaseUrl);
        
        // 延迟1秒开始验证，提供更好的用户体验
        setTimeout(() => {
            const urlParams = new URLSearchParams(window.location.search);
            const code = urlParams.get('code');
            
            if (!code) {
                this.showManualInput();
                return;
            }
            
            this.currentCode = code.trim().toUpperCase();
            this.verifyCode(this.currentCode);
        }, 1000);
    }
    
    /**
     * 验证授权码
     */
    async verifyCode(code) {
        if (!code || code.length !== 12) {
            this.showInvalid('验证码格式无效（应为12位字符）');
            return;
        }
        
        this.updateLoadingStatus('验证中...');
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/verify/${code}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
                timeout: 10000 // 10秒超时
            });
            
            if (!response.ok) {
                if (response.status === 400) {
                    const errorData = await response.json();
                    this.showInvalid(errorData.message || '验证码无效');
                } else if (response.status === 404) {
                    this.showInvalid('验证服务不可用');
                } else {
                    throw new Error(`服务器错误: ${response.status}`);
                }
                return;
            }
            
            const result = await response.json();
            
            if (result.valid) {
                this.showValid(code, result);
            } else {
                this.showInvalid(result.message || '验证码无效');
            }
            
        } catch (error) {
            console.error('验证请求失败:', error);
            
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                // 网络连接错误
                this.showNetworkError();
            } else if (this.retryCount < this.maxRetries) {
                // 重试机制
                this.retryCount++;
                this.updateLoadingStatus(`连接失败，正在重试 (${this.retryCount}/${this.maxRetries})...`);
                setTimeout(() => {
                    this.verifyCode(code);
                }, 2000 * this.retryCount); // 递增延迟
            } else {
                this.showNetworkError();
            }
        }
    }
    
    /**
     * 显示验证成功页面
     */
    showValid(code, result) {
        document.getElementById('codeDisplay').textContent = code;
        document.getElementById('verifyTime').textContent = new Date().toLocaleString('zh-CN');
        
        // 显示激活状态
        const activationStatus = document.getElementById('activationStatus');
        const activationInfo = document.getElementById('activationInfo');
        const activationTime = document.getElementById('activationTime');
        
        if (result.activated) {
            if (result.first_activation) {
                activationStatus.textContent = '首次激活';
                activationStatus.style.color = '#007700';
                activationInfo.classList.remove('hidden');
                activationTime.textContent = new Date(result.activation_date).toLocaleString('zh-CN');
            } else {
                activationStatus.textContent = '已激活';
                activationStatus.style.color = '#333333';
                if (result.activation_date) {
                    activationInfo.classList.remove('hidden');
                    activationTime.textContent = new Date(result.activation_date).toLocaleString('zh-CN');
                }
            }
        } else {
            activationStatus.textContent = '未激活';
            activationStatus.style.color = '#666666';
        }
        
        this.hideAllCards();
        document.getElementById('validCard').classList.remove('hidden');
        
        // 记录成功验证
        this.recordVerification(code, true);
    }
    
    /**
     * 显示验证失败页面
     */
    showInvalid(message = '此验证码无效或不存在') {
        document.getElementById('errorMessage').textContent = message;
        
        this.hideAllCards();
        document.getElementById('invalidCard').classList.remove('hidden');
        
        // 记录失败验证
        this.recordVerification(this.currentCode, false);
    }
    
    /**
     * 显示网络错误页面
     */
    showNetworkError() {
        this.hideAllCards();
        document.getElementById('networkErrorCard').classList.remove('hidden');
    }
    
    /**
     * 显示手动输入页面
     */
    showManualInput() {
        this.hideAllCards();
        document.getElementById('manualInputCard').classList.remove('hidden');
        
        // 聚焦到输入框
        setTimeout(() => {
            const input = document.getElementById('manualCodeInput');
            input.focus();
            
            // 添加回车键支持
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.verifyManualCode();
                }
            });
            
            // 自动转换为大写并限制输入
            input.addEventListener('input', (e) => {
                let value = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '');
                if (value.length > 12) {
                    value = value.substring(0, 12);
                }
                e.target.value = value;
            });
        }, 100);
    }
    
    /**
     * 验证手动输入的验证码
     */
    verifyManualCode() {
        const input = document.getElementById('manualCodeInput');
        const code = input.value.trim().toUpperCase();
        
        if (!code) {
            alert('请输入验证码');
            input.focus();
            return;
        }
        
        if (code.length !== 12) {
            alert('验证码应为12位字符');
            input.focus();
            return;
        }
        
        this.currentCode = code;
        this.retryCount = 0; // 重置重试计数
        
        // 显示加载状态
        this.hideAllCards();
        document.getElementById('loadingCard').classList.remove('hidden');
        
        // 开始验证
        this.verifyCode(code);
    }
    
    /**
     * 显示主要卡片（返回功能）
     */
    showMainCards() {
        // 如果有验证码参数，重新验证
        const urlParams = new URLSearchParams(window.location.search);
        const code = urlParams.get('code');
        
        if (code) {
            this.currentCode = code.trim().toUpperCase();
            this.retryCount = 0;
            this.hideAllCards();
            document.getElementById('loadingCard').classList.remove('hidden');
            this.verifyCode(this.currentCode);
        } else {
            this.showManualInput();
        }
    }
    
    /**
     * 更新加载状态文本
     */
    updateLoadingStatus(message) {
        const loadingDetail = document.getElementById('loadingDetail');
        if (loadingDetail) {
            loadingDetail.textContent = message;
        }
    }
    
    /**
     * 隐藏所有卡片
     */
    hideAllCards() {
        document.querySelectorAll('.card').forEach(card => {
            card.classList.add('hidden');
        });
    }
    
    /**
     * 记录验证信息（本地存储）
     */
    recordVerification(code, success) {
        try {
            const verifications = JSON.parse(localStorage.getItem('verifications') || '[]');
            verifications.push({
                code: code,
                success: success,
                timestamp: new Date().toISOString(),
                user_agent: navigator.userAgent,
                url: window.location.href
            });
            
            // 只保留最近50条记录
            if (verifications.length > 50) {
                verifications.splice(0, verifications.length - 50);
            }
            
            localStorage.setItem('verifications', JSON.stringify(verifications));
        } catch (error) {
            console.warn('无法保存验证记录:', error);
        }
    }
    
    /**
     * 获取客户端信息（用于统计）
     */
    getClientInfo() {
        return {
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            language: navigator.language,
            platform: navigator.platform,
            screen: `${screen.width}x${screen.height}`,
            viewport: `${window.innerWidth}x${window.innerHeight}`
        };
    }
}

// 全局函数（供HTML调用）
function showManualInput() {
    if (window.verifier) {
        window.verifier.showManualInput();
    }
}

function verifyManualCode() {
    if (window.verifier) {
        window.verifier.verifyManualCode();
    }
}

function showMainCards() {
    if (window.verifier) {
        window.verifier.showMainCards();
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    console.log('📱 页面加载完成，初始化验证器...');
    window.verifier = new BookVerifier();
    window.BookVerifier = BookVerifier; // 暴露类供错误处理使用
});

// 页面可见性变化处理
document.addEventListener('visibilitychange', () => {
    if (!document.hidden && window.verifier) {
        console.log('📱 页面重新可见');
        // 可以在这里添加重新验证逻辑
    }
});

// 网络状态变化处理
window.addEventListener('online', () => {
    console.log('🌐 网络连接恢复');
    if (window.verifier && window.verifier.currentCode) {
        // 网络恢复后自动重试
        setTimeout(() => {
            window.verifier.retryCount = 0;
            window.verifier.verifyCode(window.verifier.currentCode);
        }, 1000);
    }
});

window.addEventListener('offline', () => {
    console.log('📵 网络连接断开');
});

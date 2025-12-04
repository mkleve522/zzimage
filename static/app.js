/**
 * ZZImage 前端应用 - 适配Gitee AI接口
 */

// 预设尺寸配置
const PRESET_SIZES = {
    "1:1": [[512, 512], [1024, 1024], [2048, 2048]],
    "4:3": [[512, 384], [1024, 768], [2048, 1536]],
    "3:4": [[384, 512], [768, 1024], [1536, 2048]],
    "16:9": [[512, 288], [1024, 576], [1920, 1080]],
    "9:16": [[288, 512], [576, 1024], [1080, 1920]],
    "3:2": [[512, 341], [1024, 683], [2048, 1365]],
    "2:3": [[341, 512], [683, 1024], [1365, 2048]]
};

// 当前选择的尺寸
let currentWidth = 1024;
let currentHeight = 1024;

// DOM元素
const elements = {};

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    initElements();
    initApp();
});

// 初始化应用
function initApp() {
    // 初始化主应用组件
    initTabs();
    initSizeSelector();
    initGenerateForm();
    initCookieManagement();
    initKeyManagement();
    initModelManagement();
    initModals();
    initImagePreview();
    initLogout();
    
    // 加载初始数据
    loadCookies();
    loadApiKeys();
    loadModels();
}

// 初始化退出登录
function initLogout() {
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            try {
                await fetch('/api/auth/logout', { method: 'POST' });
            } catch (error) {
                console.error('退出登录错误:', error);
            }
            // 重定向到登录页
            window.location.href = '/login';
        });
    }
}

// 初始化DOM元素引用
function initElements() {
    elements.tabs = document.querySelectorAll('.tab-btn');
    elements.tabContents = document.querySelectorAll('.tab-content');
    elements.prompt = document.getElementById('prompt');
    elements.negativePrompt = document.getElementById('negative-prompt');
    elements.stepsInput = document.getElementById('steps-input');
    elements.generateBtn = document.getElementById('generate-btn');
    elements.resultPlaceholder = document.getElementById('result-placeholder');
    elements.resultImage = document.getElementById('result-image');
    elements.resultError = document.getElementById('result-error');
    elements.generatedImage = document.getElementById('generated-image');
    elements.errorMessage = document.getElementById('error-message');
    elements.toast = document.getElementById('toast');
}

// Tab切换
function initTabs() {
    elements.tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const targetId = tab.dataset.tab;
            
            // 更新tab状态
            elements.tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            // 更新内容显示
            elements.tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === targetId) {
                    content.classList.add('active');
                }
            });
        });
    });
}

// 尺寸选择器
function initSizeSelector() {
    const ratioButtons = document.querySelectorAll('.ratio-btn');
    const presetSizes = document.getElementById('preset-sizes');
    const customSize = document.getElementById('custom-size');
    const customWidth = document.getElementById('custom-width');
    const customHeight = document.getElementById('custom-height');
    
    // 比例按钮点击
    ratioButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            ratioButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const ratio = btn.dataset.ratio;
            
            if (ratio === 'custom') {
                presetSizes.classList.add('hidden');
                customSize.classList.remove('hidden');
                currentWidth = parseInt(customWidth.value);
                currentHeight = parseInt(customHeight.value);
            } else {
                presetSizes.classList.remove('hidden');
                customSize.classList.add('hidden');
                updatePresetSizes(ratio);
            }
        });
    });
    
    // 自定义尺寸输入
    customWidth.addEventListener('change', () => {
        currentWidth = Math.min(2048, Math.max(256, parseInt(customWidth.value) || 1024));
        customWidth.value = currentWidth;
    });
    
    customHeight.addEventListener('change', () => {
        currentHeight = Math.min(2048, Math.max(256, parseInt(customHeight.value) || 1024));
        customHeight.value = currentHeight;
    });
}

// 更新预设尺寸按钮
function updatePresetSizes(ratio) {
    const presetSizes = document.getElementById('preset-sizes');
    const sizes = PRESET_SIZES[ratio] || [[1024, 1024]];
    
    presetSizes.innerHTML = sizes.map((size, index) => {
        const [w, h] = size;
        const isActive = index === 1 ? 'active' : ''; // 默认选中中间尺寸
        return `<button class="size-btn ${isActive}" data-width="${w}" data-height="${h}">${w}×${h}</button>`;
    }).join('');
    
    // 绑定点击事件
    presetSizes.querySelectorAll('.size-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            presetSizes.querySelectorAll('.size-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentWidth = parseInt(btn.dataset.width);
            currentHeight = parseInt(btn.dataset.height);
        });
    });
    
    // 设置默认选中的尺寸（中间尺寸）
    const defaultIndex = Math.min(1, sizes.length - 1);
    currentWidth = sizes[defaultIndex][0];
    currentHeight = sizes[defaultIndex][1];
}

// 图片生成表单
function initGenerateForm() {
    elements.generateBtn.addEventListener('click', generateImage);
    
    // 下载按钮
    document.getElementById('download-btn').addEventListener('click', () => {
        const img = elements.generatedImage;
        if (img.src) {
            const a = document.createElement('a');
            a.href = img.src;
            a.download = `zzimage_${Date.now()}.png`;
            a.click();
        }
    });
    
    // 复制链接按钮
    document.getElementById('copy-url-btn').addEventListener('click', () => {
        const img = elements.generatedImage;
        if (img.src) {
            navigator.clipboard.writeText(img.src).then(() => {
                showToast('链接已复制', 'success');
            });
        }
    });
}

// 生成图片
async function generateImage() {
    const prompt = elements.prompt.value.trim();
    if (!prompt) {
        showToast('请输入提示词', 'error');
        return;
    }
    
    const steps = parseInt(elements.stepsInput.value) || 9;
    
    // 显示加载状态
    setGenerating(true);
    showResult('loading');
    
    try {
        const response = await fetch('/api/generate/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                prompt: prompt,
                negative_prompt: elements.negativePrompt.value.trim() || null,
                width: currentWidth,
                height: currentHeight,
                model: "z-image-turbo",
                num_inference_steps: steps
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            const imageUrl = data.image_url || `data:image/png;base64,${data.image_base64}`;
            elements.generatedImage.src = imageUrl;
            showResult('success');
            showToast('图片生成成功', 'success');
        } else {
            elements.errorMessage.textContent = data.error || '生成失败';
            showResult('error');
            showToast(data.error || '生成失败', 'error');
        }
    } catch (error) {
        console.error('生成错误:', error);
        elements.errorMessage.textContent = '网络错误，请重试';
        showResult('error');
        showToast('网络错误', 'error');
    } finally {
        setGenerating(false);
    }
}

// 设置生成状态
function setGenerating(isGenerating) {
    elements.generateBtn.disabled = isGenerating;
    elements.generateBtn.querySelector('.btn-text').classList.toggle('hidden', isGenerating);
    elements.generateBtn.querySelector('.btn-loading').classList.toggle('hidden', !isGenerating);
}

// 显示结果
function showResult(type) {
    elements.resultPlaceholder.classList.add('hidden');
    elements.resultImage.classList.add('hidden');
    elements.resultError.classList.add('hidden');
    
    if (type === 'success') {
        elements.resultImage.classList.remove('hidden');
    } else if (type === 'error') {
        elements.resultError.classList.remove('hidden');
    } else if (type === 'loading') {
        elements.resultPlaceholder.classList.remove('hidden');
        elements.resultPlaceholder.querySelector('p').textContent = '正在生成中...';
    } else {
        elements.resultPlaceholder.classList.remove('hidden');
        elements.resultPlaceholder.querySelector('p').textContent = '生成的图片将显示在这里';
    }
}

// Cookie管理
function initCookieManagement() {
    document.getElementById('add-cookie-btn').addEventListener('click', () => {
        openCookieModal();
    });
    
    document.getElementById('cookie-save-btn').addEventListener('click', saveCookie);
    
    // 加载每日额度配置
    loadQuotaConfig();
}

// 加载每日额度配置
async function loadQuotaConfig() {
    try {
        const response = await fetch('/api/config/quota');
        const data = await response.json();
        const quotaDisplay = document.getElementById('daily-quota-display');
        if (quotaDisplay) {
            quotaDisplay.textContent = data.daily_quota;
        }
    } catch (error) {
        console.error('加载额度配置失败:', error);
    }
}

// 加载Cookie列表
async function loadCookies() {
    try {
        const response = await fetch('/api/cookies');
        const data = await response.json();
        
        renderCookieList(data.cookies);
        updateCookieStats();
    } catch (error) {
        console.error('加载Cookie失败:', error);
    }
}

// 渲染Cookie列表
function renderCookieList(cookies) {
    const list = document.getElementById('cookie-list');
    
    if (!cookies || cookies.length === 0) {
        list.innerHTML = '<div class="list-empty">暂无Token，请添加</div>';
        return;
    }
    
    list.innerHTML = cookies.map(cookie => {
        const remaining = cookie.daily_remaining || 0;
        const used = cookie.daily_used || 0;
        const quotaClass = remaining <= 0 ? 'empty' : (remaining < 20 ? 'low' : '');
        
        return `
        <div class="list-item" data-id="${cookie.id}">
            <div class="item-info">
                <div class="item-name">
                    ${escapeHtml(cookie.name)}
                    <span class="status-badge ${cookie.is_active ? 'active' : 'inactive'}">
                        ${cookie.is_active ? '活跃' : '禁用'}
                    </span>
                </div>
                <div class="item-meta">
                    <span>总使用: ${cookie.use_count}次</span>
                    <span>错误: ${cookie.error_count}次</span>
                    ${cookie.socks5_proxy ? `<span>代理: ${escapeHtml(cookie.socks5_proxy.split('@')[1] || cookie.socks5_proxy)}</span>` : ''}
                </div>
                <div class="item-quota">今日额度: <span class="quota-value ${quotaClass}">${remaining} 剩余 (已用 ${used})</span></div>
            </div>
            <div class="item-actions">
                <button class="btn-secondary" onclick="editCookie(${cookie.id})">编辑</button>
                <button class="btn-danger" onclick="deleteCookie(${cookie.id})">删除</button>
            </div>
        </div>
    `}).join('');
}

// 更新Cookie统计
async function updateCookieStats() {
    try {
        const response = await fetch('/api/cookies/stats/overview');
        const stats = await response.json();
        
        document.getElementById('stat-total').textContent = stats.total;
        document.getElementById('stat-active').textContent = stats.active;
        document.getElementById('stat-inactive').textContent = stats.inactive;
        document.getElementById('stat-uses').textContent = stats.total_uses;
        document.getElementById('stat-error-rate').textContent = 
            (stats.error_rate * 100).toFixed(1) + '%';
    } catch (error) {
        console.error('加载统计失败:', error);
    }
}

// 打开Cookie弹窗
function openCookieModal(cookie = null) {
    const modal = document.getElementById('cookie-modal');
    const title = document.getElementById('cookie-modal-title');
    
    if (cookie) {
        title.textContent = '编辑Token';
        document.getElementById('cookie-edit-id').value = cookie.id;
        document.getElementById('cookie-name').value = cookie.name;
        document.getElementById('cookie-value').value = cookie.cookie_value;
        document.getElementById('cookie-proxy').value = cookie.socks5_proxy || '';
        document.getElementById('cookie-active').checked = cookie.is_active;
    } else {
        title.textContent = '添加Token';
        document.getElementById('cookie-edit-id').value = '';
        document.getElementById('cookie-name').value = '';
        document.getElementById('cookie-value').value = '';
        document.getElementById('cookie-proxy').value = '';
        document.getElementById('cookie-active').checked = true;
    }
    
    modal.classList.remove('hidden');
}

// 编辑Cookie
async function editCookie(id) {
    try {
        const response = await fetch(`/api/cookies/${id}`);
        const cookie = await response.json();
        openCookieModal(cookie);
    } catch (error) {
        showToast('加载Token失败', 'error');
    }
}

// 保存Cookie
async function saveCookie() {
    const id = document.getElementById('cookie-edit-id').value;
    const name = document.getElementById('cookie-name').value.trim();
    const cookieValue = document.getElementById('cookie-value').value.trim();
    const proxy = document.getElementById('cookie-proxy').value.trim();
    const isActive = document.getElementById('cookie-active').checked;
    
    if (!name || !cookieValue) {
        showToast('请填写必填项', 'error');
        return;
    }
    
    try {
        const url = id ? `/api/cookies/${id}` : '/api/cookies';
        const method = id ? 'PUT' : 'POST';
        
        const body = {
            name,
            cookie_value: cookieValue,
            socks5_proxy: proxy || null,
            is_active: isActive
        };
        
        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        
        if (response.ok) {
            showToast(id ? 'Token已更新' : 'Token已添加', 'success');
            closeModal('cookie-modal');
            loadCookies();
        } else {
            const error = await response.json();
            showToast(error.detail || '保存失败', 'error');
        }
    } catch (error) {
        showToast('保存失败', 'error');
    }
}

// 删除Cookie
async function deleteCookie(id) {
    if (!confirm('确定要删除此Token吗？')) return;
    
    try {
        const response = await fetch(`/api/cookies/${id}`, { method: 'DELETE' });
        if (response.ok) {
            showToast('Token已删除', 'success');
            loadCookies();
        } else {
            showToast('删除失败', 'error');
        }
    } catch (error) {
        showToast('删除失败', 'error');
    }
}

// API密钥管理
function initKeyManagement() {
    document.getElementById('add-key-btn').addEventListener('click', () => {
        document.getElementById('key-name').value = '';
        document.getElementById('key-modal').classList.remove('hidden');
    });
    
    document.getElementById('key-save-btn').addEventListener('click', createApiKey);
    
    document.getElementById('copy-key-btn').addEventListener('click', () => {
        const key = document.getElementById('new-key-value').textContent;
        navigator.clipboard.writeText(key).then(() => {
            showToast('密钥已复制', 'success');
        });
    });
}

// 加载API密钥列表
async function loadApiKeys() {
    try {
        const response = await fetch('/api/keys');
        const data = await response.json();
        renderKeyList(data.keys);
    } catch (error) {
        console.error('加载API密钥失败:', error);
    }
}

// 渲染API密钥列表
function renderKeyList(keys) {
    const list = document.getElementById('key-list');
    
    if (!keys || keys.length === 0) {
        list.innerHTML = '<div class="list-empty">暂无API密钥，请创建</div>';
        return;
    }
    
    list.innerHTML = keys.map(key => `
        <div class="list-item" data-id="${key.id}">
            <div class="item-info">
                <div class="item-name">${escapeHtml(key.name)}</div>
                <div class="item-meta">
                    <span>密钥: ${key.key.substring(0, 10)}...${key.key.substring(key.key.length - 4)}</span>
                    <span>创建: ${key.created_at || '未知'}</span>
                </div>
            </div>
            <div class="item-actions">
                <button class="btn-danger" onclick="deleteApiKey(${key.id})">删除</button>
            </div>
        </div>
    `).join('');
}

// 创建API密钥
async function createApiKey() {
    const name = document.getElementById('key-name').value.trim();
    
    if (!name) {
        showToast('请输入密钥名称', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/keys', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        
        if (response.ok) {
            const data = await response.json();
            closeModal('key-modal');
            
            // 显示新密钥
            document.getElementById('new-key-value').textContent = data.key;
            document.getElementById('key-created-modal').classList.remove('hidden');
            
            loadApiKeys();
        } else {
            const error = await response.json();
            showToast(error.detail || '创建失败', 'error');
        }
    } catch (error) {
        showToast('创建失败', 'error');
    }
}

// 删除API密钥
async function deleteApiKey(id) {
    if (!confirm('确定要删除此API密钥吗？删除后使用此密钥的应用将无法访问。')) return;
    
    try {
        const response = await fetch(`/api/keys/${id}`, { method: 'DELETE' });
        if (response.ok) {
            showToast('API密钥已删除', 'success');
            loadApiKeys();
        } else {
            showToast('删除失败', 'error');
        }
    } catch (error) {
        showToast('删除失败', 'error');
    }
}

// 模型配置管理
function initModelManagement() {
    const addModelBtn = document.getElementById('add-model-btn');
    if (addModelBtn) {
        addModelBtn.addEventListener('click', () => {
            openModelModal();
        });
    }
    
    const modelSaveBtn = document.getElementById('model-save-btn');
    if (modelSaveBtn) {
        modelSaveBtn.addEventListener('click', saveModel);
    }
}

// 加载模型列表
async function loadModels() {
    try {
        const response = await fetch('/api/models');
        if (response.ok) {
            const data = await response.json();
            renderModelList(data.models || []);
        }
    } catch (error) {
        console.error('加载模型配置失败:', error);
    }
}

// 渲染模型列表
function renderModelList(models) {
    const list = document.getElementById('model-list');
    if (!list) return;
    
    if (!models || models.length === 0) {
        list.innerHTML = '<div class="list-empty">暂无自定义模型，请添加</div>';
        return;
    }
    
    list.innerHTML = models.map(model => `
        <div class="list-item" data-id="${model.id}">
            <div class="item-info">
                <div class="item-name">
                    ${escapeHtml(model.name)}
                    ${model.is_default ? '<span class="status-badge active">默认</span>' : ''}
                    ${model.use_markdown ? '<span class="status-badge">MD</span>' : ''}
                </div>
                <div class="item-meta">
                    <span>尺寸: ${model.width}×${model.height}</span>
                    <span>步数: ${model.steps}</span>
                    ${model.description ? `<span>${escapeHtml(model.description)}</span>` : ''}
                </div>
            </div>
            <div class="item-actions">
                <button class="btn-secondary" onclick="editModel(${model.id})">编辑</button>
                <button class="btn-danger" onclick="deleteModel(${model.id})">删除</button>
            </div>
        </div>
    `).join('');
}

// 打开模型弹窗
function openModelModal(model = null) {
    const modal = document.getElementById('model-modal');
    if (!modal) return;
    
    const title = document.getElementById('model-modal-title');
    
    if (model) {
        title.textContent = '编辑模型';
        document.getElementById('model-edit-id').value = model.id;
        document.getElementById('model-name').value = model.name;
        document.getElementById('model-width').value = model.width;
        document.getElementById('model-height').value = model.height;
        document.getElementById('model-steps').value = model.steps;
        document.getElementById('model-description').value = model.description || '';
        document.getElementById('model-default').checked = model.is_default;
        document.getElementById('model-markdown').checked = model.use_markdown !== false;
    } else {
        title.textContent = '添加模型';
        document.getElementById('model-edit-id').value = '';
        document.getElementById('model-name').value = '';
        document.getElementById('model-width').value = '1024';
        document.getElementById('model-height').value = '1024';
        document.getElementById('model-steps').value = '9';
        document.getElementById('model-description').value = '';
        document.getElementById('model-default').checked = false;
        document.getElementById('model-markdown').checked = true;
    }
    
    modal.classList.remove('hidden');
}

// 编辑模型
async function editModel(id) {
    try {
        const response = await fetch(`/api/models/${id}`);
        if (response.ok) {
            const model = await response.json();
            openModelModal(model);
        } else {
            showToast('加载模型失败', 'error');
        }
    } catch (error) {
        showToast('加载模型失败', 'error');
    }
}

// 保存模型
async function saveModel() {
    const id = document.getElementById('model-edit-id').value;
    const name = document.getElementById('model-name').value.trim();
    const width = parseInt(document.getElementById('model-width').value);
    const height = parseInt(document.getElementById('model-height').value);
    const steps = parseInt(document.getElementById('model-steps').value);
    const description = document.getElementById('model-description').value.trim();
    const isDefault = document.getElementById('model-default').checked;
    const useMarkdown = document.getElementById('model-markdown').checked;
    
    if (!name) {
        showToast('请输入模型名称', 'error');
        return;
    }
    
    if (width < 256 || width > 2048 || height < 256 || height > 2048) {
        showToast('尺寸必须在256-2048之间', 'error');
        return;
    }
    
    try {
        const url = id ? `/api/models/${id}` : '/api/models';
        const method = id ? 'PUT' : 'POST';
        
        const body = {
            name,
            width,
            height,
            steps,
            description: description || null,
            is_default: isDefault,
            use_markdown: useMarkdown
        };
        
        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        
        if (response.ok) {
            showToast(id ? '模型已更新' : '模型已添加', 'success');
            closeModal('model-modal');
            loadModels();
        } else {
            const error = await response.json();
            showToast(error.detail || '保存失败', 'error');
        }
    } catch (error) {
        showToast('保存失败', 'error');
    }
}

// 删除模型
async function deleteModel(id) {
    if (!confirm('确定要删除此模型配置吗？')) return;
    
    try {
        const response = await fetch(`/api/models/${id}`, { method: 'DELETE' });
        if (response.ok) {
            showToast('模型已删除', 'success');
            loadModels();
        } else {
            showToast('删除失败', 'error');
        }
    } catch (error) {
        showToast('删除失败', 'error');
    }
}

// 弹窗管理
function initModals() {
    // 关闭按钮
    document.querySelectorAll('.modal-close, .modal-cancel').forEach(btn => {
        btn.addEventListener('click', () => {
            const modal = btn.closest('.modal');
            if (modal) modal.classList.add('hidden');
        });
    });
    
    // 点击背景关闭
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.add('hidden');
            }
        });
    });
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.add('hidden');
}

// Toast提示
function showToast(message, type = 'info') {
    const toast = elements.toast;
    toast.textContent = message;
    toast.className = `toast ${type}`;
    
    // 显示
    setTimeout(() => toast.classList.remove('hidden'), 10);
    
    // 自动隐藏
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}

// HTML转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 图片预览功能
function initImagePreview() {
    const previewModal = document.getElementById('image-preview-modal');
    const previewImage = document.getElementById('preview-image');
    const previewClose = previewModal.querySelector('.preview-close');
    const previewOverlay = previewModal.querySelector('.preview-overlay');
    const generatedImage = document.getElementById('generated-image');
    
    // 点击生成的图片打开预览
    generatedImage.addEventListener('click', () => {
        if (generatedImage.src) {
            previewImage.src = generatedImage.src;
            previewModal.classList.remove('hidden');
        }
    });
    
    // 关闭预览
    function closePreview() {
        previewModal.classList.add('hidden');
    }
    
    previewClose.addEventListener('click', closePreview);
    previewOverlay.addEventListener('click', closePreview);
    
    // ESC键关闭预览
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !previewModal.classList.contains('hidden')) {
            closePreview();
        }
    });
}
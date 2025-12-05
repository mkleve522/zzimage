# ZZImage - 文生图服务

基于Gitee AI的文生图服务，支持Cookie池轮询、SOCKS5代理、OpenAI兼容接口。

## 功能特性

- 🎨 **文生图**: 通过提示词生成图片，基于Gitee AI的z-image-turbo模型
- 🔄 **Token池轮询**: 支持多Token负载均衡，自动轮询调度
- 📊 **每日额度管理**: 自动跟踪每个Token的每日使用量（默认100次/天）
- 🌐 **SOCKS5代理**: 每个Token可配置独立的SOCKS5代理
- 🔌 **OpenAI兼容接口**: 提供标准OpenAI格式的 `/v1/images/generations` 和 `/v1/chat/completions` 接口
- 💬 **Chat对话接口**: 支持通过Chat接口生成图片，兼容各种AI工具
- 📐 **灵活尺寸**: 支持多种预设比例和自定义尺寸（最大2048×2048）
- 🔑 **API密钥管理**: 支持创建和管理多个API密钥
- ⚙️ **自定义模型配置**: 可配置不同模型名称对应不同的默认参数
- 🔐 **管理员认证**: 管理页面需要登录认证

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python run.py
```

服务将在 http://localhost:8000 启动。

### 3. 访问界面

- **前端界面**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **ReDoc文档**: http://localhost:8000/redoc

## 使用说明

### 获取Gitee AI Token

1. 访问 [ai.gitee.com](https://ai.gitee.com)
2. 注册/登录账号
3. 获取API Token

### 添加Token

1. 打开前端界面，点击"Cookie管理"标签
2. 点击"添加Cookie"按钮
3. 填写Token名称、Token值（从Gitee AI获取）
4. （可选）配置SOCKS5代理，格式：`socks5://user:pass@host:port`
5. 点击保存

### 生成图片

1. 在"图片生成"页面输入提示词
2. 设置推理步数（默认9，使用z-image-turbo模型）
3. 选择图片尺寸（预设比例或自定义）
4. 点击"生成图片"按钮

### 使用OpenAI兼容接口

1. 在"API密钥"页面创建一个API密钥
2. 使用以下格式调用接口：

**图片生成接口:**
```bash
curl -X POST http://localhost:8000/v1/images/generations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "z-image-turbo",
    "prompt": "一只可爱的猫咪",
    "size": "1024x1024",
    "n": 1
  }'
```

**Chat对话接口:**
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "z-image",
    "messages": [
      {"role": "user", "content": "画一只可爱的猫咪 --size 1024x768"}
    ]
  }'
```

Chat接口支持在提示词中使用参数：
- `--size 1024x768`: 设置图片尺寸
- `--width 1024`: 设置宽度
- `--height 768`: 设置高度
- `--steps 9`: 设置推理步数

### 自定义模型配置

1. 在"模型配置"页面添加自定义模型
2. 设置模型名称、默认尺寸、推理步数等参数
3. 通过Chat接口调用时使用自定义模型名称

## API接口

### 图片生成

#### POST /api/generate/
生成图片（内部接口）

```json
{
  "prompt": "提示词",
  "negative_prompt": "负向提示词（可选）",
  "width": 1024,
  "height": 1024,
  "model": "z-image-turbo",
  "num_inference_steps": 9
}
```

#### POST /v1/images/generations
OpenAI兼容接口（需要API密钥）

```json
{
  "model": "z-image-turbo",
  "prompt": "提示词",
  "size": "1024x1024",
  "n": 1,
  "response_format": "url"
}
```

#### POST /v1/chat/completions
Chat对话接口（需要API密钥）

```json
{
  "model": "z-image",
  "messages": [
    {"role": "user", "content": "画一只可爱的猫咪"}
  ],
  "stream": false
}
```

响应格式：
```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "z-image",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "![Generated Image](image_url)\n\n图片已生成成功！"
    },
    "finish_reason": "stop"
  }]
}
```

### Token管理

- `GET /api/cookies` - 获取所有Token
- `POST /api/cookies` - 添加Token
- `PUT /api/cookies/{id}` - 更新Token
- `DELETE /api/cookies/{id}` - 删除Token
- `GET /api/cookies/stats/overview` - 获取统计信息

### API密钥管理

- `GET /api/keys` - 获取所有API密钥
- `POST /api/keys` - 创建API密钥
- `DELETE /api/keys/{id}` - 删除API密钥

### 模型配置管理

- `GET /api/models` - 获取所有模型配置
- `POST /api/models` - 添加模型配置
- `PUT /api/models/{id}` - 更新模型配置
- `DELETE /api/models/{id}` - 删除模型配置

### 认证接口

- `POST /api/auth/login` - 管理员登录
- `POST /api/auth/logout` - 退出登录
- `GET /api/auth/status` - 检查登录状态

## 支持的模型

| 模型 | 说明 | 推荐步数 |
|------|------|----------|
| z-image-turbo | 快速生成模型 | 9 |

## Docker 部署（含 ARM）

以下步骤在 ARM 服务器（如 ARM64）上验证通过，镜像基于多架构的 `python:3.11-slim`，默认使用项目自带的 `python run.py` 启动方式。



```dockerfile
FROM python:3.11-slim


COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

### 2. 本机（ARM）构建镜像

ARM 服务器直接构建即可，Docker 会自动拉取 ARM 架构基础镜像：

```bash
docker build -t zzimage:arm .
```

> 如果镜像较大或网络慢，可加 `--pull` 强制拉取最新基础镜像，避免旧缓存导致的漏洞或缺包。

### 3. x86 上为 ARM 交叉构建（可选）

如果只有 x86 机器但需要给 ARM 服务器准备镜像，先启用 buildx（Docker Desktop 默认开启，多数服务器需手动创建）：

```bash
docker buildx create --use --name zzimage-arm-builder
docker buildx inspect --bootstrap
```

然后使用 `--platform linux/arm64` 构建并推送到仓库（或导出为 tar 再传到 ARM 服务器）：

```bash
docker buildx build \
  --platform linux/arm64 \
  -t your-registry/zzimage:arm \
  --push .
```

如果不方便推送，也可改用 `--output type=tar,dest=zzimage_arm.tar` 导出后在 ARM 服务器上 `docker load -i zzimage_arm.tar` 导入。

### 4. ARM 服务器运行容器

```bash
docker run -d \
  -p 8000:8000 \
  -e HOST=0.0.0.0 \
  -e PORT=8000 \
  -e ADMIN_USERNAME=your_admin \
  -e ADMIN_PASSWORD=strong_password \
  -v $(pwd)/data:/app/data \
  --name zzimage \
  zzimage:arm
```

- `-v $(pwd)/data:/app/data` 挂载数据目录，持久化数据库和密钥，确保宿主机 `data/` 目录有写权限。
- ARM 服务器上直接运行即可，无需额外 QEMU 配置；若端口需变更，调整 `-p` 与 `PORT` 环境变量即可。

### 5. 验证与管理

- 首次启动后访问 `http://<服务器IP>:8000`，API 文档在 `/docs`。
- 查看实时日志：`docker logs -f zzimage`
- 停止/启动：`docker stop zzimage` / `docker start zzimage`
- 更新镜像后重新部署：`docker pull <镜像>`，然后 `docker rm -f zzimage && <docker run ...>`

## 预设尺寸

| 比例 | 可选尺寸 |
|------|----------|
| 1:1 | 512×512, 1024×1024, 2048×2048 |
| 4:3 | 512×384, 1024×768, 2048×1536 |
| 3:4 | 384×512, 768×1024, 1536×2048 |
| 16:9 | 512×288, 1024×576, 1920×1080 |
| 9:16 | 288×512, 576×1024, 1080×1920 |
| 3:2 | 512×341, 1024×683, 2048×1365 |
| 2:3 | 341×512, 683×1024, 1365×2048 |

自定义尺寸范围：256 - 2048

## 配置说明

可通过环境变量配置：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| HOST | 0.0.0.0 | 监听地址 |
| PORT | 8000 | 监听端口 |
| DAILY_QUOTA | 100 | 每个Token每日额度 |
| REQUEST_TIMEOUT | 120 | 请求超时（秒） |
| MAX_RETRIES | 3 | 最大重试次数 |
| ADMIN_USERNAME | admin | 管理员用户名 |
| ADMIN_PASSWORD | admin123 | 管理员密码 |

## 项目结构

```
zzimage/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI入口
│   ├── config.py            # 配置管理
│   ├── database.py          # 数据库模型
│   ├── routers/
│   │   ├── generate.py      # 图片生成接口
│   │   ├── openai.py        # OpenAI兼容接口（含Chat）
│   │   ├── cookies.py       # Token管理接口
│   │   ├── models.py        # 模型配置接口
│   │   └── auth.py          # 认证接口
│   └── services/
│       ├── cookie_pool.py   # Token池服务
│       └── image_gen.py     # 图片生成服务
├── static/
│   ├── index.html           # 前端页面
│   ├── style.css
│   └── app.js
├── data/                    # 数据目录（自动创建）
│   └── zzimage.db          # SQLite数据库
├── requirements.txt
├── run.py                   # 启动脚本
└── README.md
```

## 注意事项

1. **Token获取**: 需要在 [ai.gitee.com](https://ai.gitee.com) 注册并获取API Token
2. **代理格式**: SOCKS5代理格式为 `socks5://user:pass@host:port`，无认证时为 `socks5://host:port`
3. **尺寸限制**: 最大支持2048×2048，最小256×256
4. **默认密码**: 首次使用请修改默认管理员密码（通过环境变量配置）
5. **Chat接口**: 支持流式输出，可在各种AI工具中使用

## License

MIT
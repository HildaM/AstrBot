# AstrBot macOS 快速启动指南

本文档面向 macOS 用户，涵盖**两种启动方式**：一键安装（推荐普通用户）和源码开发（推荐开发者）。

---

## 环境要求

| 依赖 | 版本要求 | 说明 |
|------|---------|------|
| macOS | 12+ | Intel / Apple Silicon 均支持 |
| Python | >= 3.12 | 源码开发方式需要 |
| uv | 最新版 | Python 包管理器 |
| Node.js | >= 18 | 仅开发 Dashboard 时需要 |
| pnpm | >= 8 | 仅开发 Dashboard 时需要 |

---

## 方式一：一键安装（推荐）

适合快速体验 AstrBot，无需 clone 源码。

### 1. 安装 uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

安装完成后重新打开终端，或执行：

```bash
source $HOME/.local/bin/env
```

验证安装：

```bash
uv --version
```

### 2. 安装并初始化 AstrBot

```bash
uv tool install astrbot
astrbot init    # 仅首次需要，初始化配置和数据目录
```

> **注意**：macOS 安全检查可能导致首次运行 `astrbot` 命令需要 10-20 秒，这是正常现象。

### 3. 启动

```bash
astrbot run
```

启动成功后，打开浏览器访问：

```
http://localhost:6185
```

即可进入 AstrBot 管理面板，在面板中可视化配置 LLM 供应商、消息平台等。

### 4. 更新

```bash
uv tool upgrade astrbot
```

---

## 方式二：源码开发

适合需要修改代码、开发插件或贡献 PR 的开发者。

### 1. 安装 uv

同上方式一。

### 2. Clone 项目

```bash
git clone https://github.com/AstrBotDevs/AstrBot.git
cd AstrBot
```

### 3. 安装依赖

```bash
uv sync
```

这会自动创建 `.venv` 虚拟环境并安装所有依赖（约 150 个包）。

如需安装开发依赖（ruff、pytest 等）：

```bash
uv sync --group dev
```

### 4. 启动后端

```bash
uv run main.py
```

启动后 API 服务默认监听：

```
http://localhost:6185
```

首次启动会自动下载管理面板静态文件（dist），如果网络较慢，也可以手动从 [Releases](https://github.com/AstrBotDevs/AstrBot/releases/latest) 下载 `dist.zip`，解压到 `data/dist/` 目录。

### 5. 启动 Dashboard 开发服务（可选）

如果需要修改前端代码，可以启动 Dashboard 开发服务器：

```bash
# 安装 pnpm（如果没有）
npm install -g pnpm

# 安装前端依赖（仅首次）
cd dashboard
pnpm install

# 启动开发服务器
pnpm dev
```

Dashboard 开发服务默认运行在：

```
http://localhost:3000
```

开发服务器会自动代理 API 请求到后端的 `localhost:6185`。

---

## 首次配置

启动成功后，打开 `http://localhost:6185` 进入管理面板，完成以下基础配置：

### 1. 配置 LLM 供应商

在管理面板 **「供应商管理」** 页面，添加你的 LLM 服务：

| 供应商 | 需要的信息 |
|--------|-----------|
| OpenAI / 兼容 API | API Key + Base URL |
| Google Gemini | API Key |
| DeepSeek | API Key |
| Ollama（本地） | 模型名称（无需 Key） |

> 推荐先使用 OpenAI 兼容 API 或 DeepSeek 快速上手。

### 2. 配置消息平台（可选）

在 **「平台管理」** 页面，选择你需要接入的平台：

- **Web ChatUI**（内置，无需额外配置）
- **QQ**（通过 NapCat/OneBot v11）
- **Telegram**（需要 Bot Token）
- **企业微信 / 飞书 / 钉钉 / Slack** 等

### 3. 开始对话

配置完成后，可以直接在管理面板的 **ChatUI** 中与 AI 对话，或通过已接入的消息平台发送消息。

---

## 项目结构速览

```
AstrBot/
├── main.py                  # 主入口
├── astrbot/
│   ├── core/                # 核心业务逻辑
│   │   ├── agent/           # Agent 框架（运行器、工具、上下文）
│   │   ├── cron/            # 定时任务系统（APScheduler）
│   │   ├── pipeline/        # 消息处理流水线（9 阶段洋葱模型）
│   │   ├── platform/        # 消息平台适配器
│   │   ├── provider/        # LLM 供应商适配
│   │   ├── star/            # 插件系统（Star = 插件）
│   │   ├── knowledge_base/  # 知识库（向量检索）
│   │   └── config/          # 配置管理
│   ├── cli/                 # CLI 工具（init / run / conf / plug）
│   ├── dashboard/           # Dashboard API 路由
│   └── api/                 # 公共 API
├── dashboard/               # 前端项目（Vue 3 + Vuetify）
├── data/                    # 运行时数据（启动后生成）
│   ├── cmd_config.json      # 核心配置文件
│   ├── data_v4.db           # SQLite 数据库
│   └── dist/                # 管理面板静态文件
├── pyproject.toml           # Python 项目配置
└── compose.yml              # Docker Compose 配置
```

---

## 常用命令

### 后端

```bash
# 启动
uv run main.py

# 指定 WebUI 目录启动（开发时可用）
uv run main.py --webui-dir ./dashboard/dist

# 代码格式化
uv run ruff format .

# 代码检查
uv run ruff check .

# 运行测试
uv run pytest

# PR 前验证
make pr-test-neo
```

### Dashboard

```bash
cd dashboard
pnpm dev          # 开发服务器
pnpm build        # 生产构建
pnpm typecheck    # 类型检查
pnpm lint         # ESLint 检查
```

### CLI 工具

```bash
astrbot init      # 初始化环境
astrbot run       # 启动 AstrBot
astrbot conf      # 配置管理
astrbot plug      # 插件管理
```

---

## 常见问题

### Q: 首次运行 `astrbot` 命令很慢？

macOS 的 Gatekeeper 安全检查会导致首次执行约 10-20 秒延迟，后续运行正常。

### Q: `uv sync` 报错？

确保 Python 版本 >= 3.12：

```bash
python3 --version
```

如果版本不对，可以用 uv 安装指定版本：

```bash
uv python install 3.12
```

### Q: Dashboard 下载失败？

手动下载：前往 [Releases](https://github.com/AstrBotDevs/AstrBot/releases/latest) 下载 `dist.zip`，解压到 `data/dist/` 目录。

### Q: 端口 6185 被占用？

查找占用进程：

```bash
lsof -i :6185
```

终止进程或修改配置中的端口。

### Q: Apple Silicon 兼容性问题？

项目的所有依赖均支持 ARM64 架构。如果个别包出现问题，尝试：

```bash
arch -arm64 uv sync
```

---

## 更多资源

- [官方文档](https://astrbot.app/)
- [插件市场](https://astrbot.app/)
- [GitHub Issues](https://github.com/AstrBotDevs/AstrBot/issues)
- [社区 QQ 群](https://github.com/AstrBotDevs/AstrBot#-社区)
- [Discord](https://discord.gg/hAVk6tgV36)

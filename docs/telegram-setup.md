# Telegram 频道配置

Telegram 接入有两种方式：

| 方式 | 需要 | 适合 |
|------|------|------|
| **方式 A：官方 Channel 插件** | Claude Pro/Max 订阅 | 有订阅、图省事 |
| **方式 B：Python Bot** | Anthropic API key（或兼容 API） | 用 API、要定制、想省钱 |

两种方式都需要先创建 Telegram Bot。

## 前置条件

- 已安装 Claude Code CLI
- 一个 Telegram Bot Token（从 @BotFather 获取）

## 创建 Telegram Bot（两种方式通用）

1. 打开 Telegram，搜索 `@BotFather`
2. 发送 `/newbot`
3. 按提示设置 bot 名称
4. 获取 Bot Token（格式：`123456789:ABCdef...`）
5. 保存好 Token

获取你的 Telegram user ID：给 `@userinfobot` 发消息即可。

---

## 方式 A：官方 Channel 插件

> **重要**：官方插件 **仅支持 Claude 订阅用户**（Pro / Max），不支持 API key。

### 1. 配置 Channel

运行以下命令启动配置 skill：

```bash
cd ~/claude-workspace
claude
```

进入 Claude 后输入 `/telegram:configure`，按提示粘贴 Bot Token。

或者手动配置：

```bash
mkdir -p ~/.claude/channels/telegram
echo "TELEGRAM_BOT_TOKEN=你的Token" > ~/.claude/channels/telegram/.env
```

### 2. 配置访问控制

创建 `~/.claude/channels/telegram/access.json`：

```json
{
  "dmPolicy": "pairing",
  "allowFrom": [],
  "groups": {},
  "pending": {}
}
```

- `dmPolicy: "pairing"` 表示新用户需要配对确认
- 配对后用户 ID 会自动加入 `allowFrom`
- 也可以直接把你的 Telegram user ID 写进 `allowFrom`

### 3. 启动

```bash
claude --model claude-opus-4-6 --channels plugin:telegram@claude-plugins-official
```

### 4. 配对

首次使用时，在 Telegram 给你的 bot 发消息，终端会出现配对请求，输入 `/telegram:access` 批准。

### 5. settings.json 配置

在 `~/.claude/settings.json` 中添加 Telegram 工具的自动授权：

```json
{
  "permissions": {
    "allow": [
      "mcp__plugin_telegram_telegram__reply",
      "mcp__plugin_telegram_telegram__react",
      "mcp__plugin_telegram_telegram__edit_message",
      "mcp__plugin_telegram_telegram__download_attachment"
    ]
  }
}
```

这样 Claude 回复 Telegram 消息时不需要每次手动批准。

---

## 方式 B：Python Bot（claude-code-telegram）

使用开源项目 [claude-code-telegram](https://github.com/RichardAtCT/claude-code-telegram)，通过 Anthropic API（或任何兼容 API）驱动，不需要 Claude 订阅。

### 1. 安装

```bash
cd ~
git clone https://github.com/RichardAtCT/claude-code-telegram.git
cd claude-code-telegram
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
cat > .env << 'EOF'
TELEGRAM_BOT_TOKEN=你的Bot_Token
TELEGRAM_BOT_USERNAME=你的bot用户名
APPROVED_DIRECTORY=/home/ubuntu
ALLOWED_USERS=你的Telegram_user_ID

USE_SDK=true
ANTHROPIC_API_KEY=你的API_Key

CLAUDE_MAX_TURNS=50
CLAUDE_TIMEOUT_SECONDS=300

DATABASE_URL=sqlite:///data/bot.db
SESSION_TIMEOUT_HOURS=24
MAX_SESSIONS_PER_USER=5

ENABLE_GIT_INTEGRATION=true
ENABLE_FILE_UPLOADS=true
ENABLE_QUICK_ACTIONS=false
ENABLE_CONVERSATION_MODE=true

LOG_LEVEL=INFO
ENVIRONMENT=production
EOF
```

**关键字段说明：**

- `TELEGRAM_BOT_TOKEN`：从 @BotFather 获取的 token
- `TELEGRAM_BOT_USERNAME`：bot 的用户名（不带 @）
- `ALLOWED_USERS`：你的 Telegram user ID，逗号分隔可加多个
- `ANTHROPIC_API_KEY`：Anthropic API key，也支持兼容 API

**使用兼容 API（如 OpenRouter、中转站）：** 启动时设置 `ANTHROPIC_BASE_URL` 环境变量：

```bash
ANTHROPIC_BASE_URL=http://你的中转地址 python -m src.main
```

### 3. 启动

```bash
cd ~/claude-code-telegram
source venv/bin/activate
python -m src.main
```

后台运行：

```bash
cd ~/claude-code-telegram
source venv/bin/activate
nohup python -m src.main >> /tmp/claude-tg-bot.log 2>&1 &
```

推荐用 tmux + systemd 管理，见 [后台运行指南](background-running.md)。

### 4. 功能

Python bot 默认以 agentic 模式运行，支持：

- `/start` — 启动
- `/new` — 新建 session
- `/status` — 查看状态
- `/verbose 0|1|2` — 控制输出详细程度
- 文件上传、图片处理、语音转文字
- Session 自动恢复
- 流式输出进度显示

---

## 代理设置（国内服务器必看）

如果服务器在国内或无法直连 Telegram API，需要配置代理。

### 方法 1：环境变量

在启动脚本或 systemd service 中添加：

```bash
export HTTPS_PROXY=http://127.0.0.1:7890
export HTTP_PROXY=http://127.0.0.1:7890
```

### 方法 2：系统级代理

确保代理软件（clash / v2ray 等）在启动前运行。

### 常见症状

- bot 创建成功但收不到消息 → 大概率是代理问题
- 发消息后无反应 → 检查连接是否成功（看启动日志）
- 间歇性断连 → 代理不稳定，考虑更换节点

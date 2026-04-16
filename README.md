# Claude Code Daily

让 Claude Code 24 小时在线，通过 Telegram / 微信随时对话，具备跨 session 长期记忆。

适用场景：日常助手、知识管理、项目协作、消息代理，或任何需要 Claude 持续在线的场景。

本指南基于实际运行环境整理，核心组件全部使用现成工具拼装，无需自己写代码。

## 架构概览

```
┌─────────────────────────────────────────────────┐
│              Claude Code CLI                     │
│        (claude-opus-4-6 / 任意模型)              │
├─────────────────────────────────────────────────┤
│  CLAUDE.md (行为指令 / 工具配置 / 上下文)        │
│  Memory (auto memory 或 Memos 长期记忆)          │
├──────────┬──────────┬───────────────────────────┤
│ Telegram │  WeChat  │  其他 Channel (未来扩展)   │
│ Channel  │ Channel  │                           │
└──────────┴──────────┴───────────────────────────┘
         ↓                ↓
   Telegram Bot      微信客服号
         ↓                ↓
       用户手机 / 桌面端
```

**运行环境**：Linux 服务器（推荐）或 Mac mini，需要 24 小时在线。

## 你需要什么

| 组件 | 用途 | 必选 |
|------|------|------|
| Claude Code CLI | 核心，跑模型 | 是 |
| Claude 订阅 或 API key | 订阅用官方 Channel，API 用 Python bot，**二选一** | 是 |
| CLAUDE.md | 行为规则和上下文 | 是 |
| Telegram Channel | Telegram 聊天 | 二选一 |
| WeChat Channel | 微信聊天 | 二选一 |
| Memos | 跨 session 长期记忆 | 推荐 |
| systemd + tmux | 后台常驻 + 自动重启 | 推荐 |

### Telegram 接入方式对比

| | 官方 Channel 插件 | Python Bot（claude-code-telegram） |
|---|---|---|
| 认证方式 | Claude Pro/Max 订阅 | Anthropic API key（或兼容 API） |
| 安装难度 | 一条命令 | 需要 clone + 配置 |
| 功能 | 基础聊天 | 完整功能（session 管理、文件上传、流式输出等） |
| 可定制性 | 低（官方插件） | 高（开源 Python 项目） |
| 适合场景 | 有订阅、图省事 | 用 API、要定制、想省钱 |

## 快速开始

### 1. 安装 Claude Code

```bash
# 安装 Node.js (v18+)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo bash -
sudo apt-get install -y nodejs

# 安装 bun（某些 channel 需要）
curl -fsSL https://bun.sh/install | bash

# 安装 Claude Code
npm install -g @anthropic-ai/claude-code

# 登录
claude auth login
```

### 2. 创建工作区

```bash
mkdir -p ~/claude-workspace
cd ~/claude-workspace
```

### 3. 写 CLAUDE.md

在工作区根目录创建 `CLAUDE.md`，这是 Claude 的指令文件，每次启动自动加载。你可以在里面定义 Claude 的行为规则、输出风格、可用工具等。

参考 [examples/CLAUDE.md.example](examples/CLAUDE.md.example) 编写你自己的版本。

### 4. 接入聊天渠道

- [Telegram 配置指南](docs/telegram-setup.md)
- [微信配置指南](docs/wechat-setup.md)

### 5. 配置长期记忆（推荐）

- [Memos 记忆系统配置](docs/memos-setup.md)

### 6. 后台运行 + 自动重启

- [后台运行指南](docs/background-running.md)

## 为什么要跑两个 Session

推荐同时运行两个 Claude Code 实例（比如一个接 Telegram、一个接微信），除了多渠道之外还有一个关键原因：**互为 Watchdog**。

Claude Code 在无人值守运行时，偶尔会卡在权限确认上不动。如果只有一个 session，你只能 SSH 上去手动处理。两个 session 互相监控，一个卡住了可以让另一个去终端操作恢复。

详见 [后台运行指南](docs/background-running.md) 中的多实例配置。

## 权限配置（重要）

Claude Code 默认每次调用工具都需要用户手动批准。24 小时无人值守运行时，这会导致 Claude 频繁卡住等待确认。

**推荐配置**：在 `settings.json` 中开启 `bypassPermissions` 或至少把常用工具加入 allow 列表：

```json
{
  "permissions": {
    "allow": [
      "mcp__plugin_telegram_telegram__reply",
      "mcp__plugin_telegram_telegram__react",
      "mcp__wechat__wechat_reply",
      "mcp__wechat__wechat_send_image"
    ],
    "defaultMode": "bypassPermissions"
  }
}
```

> **注意**：`bypassPermissions` 会让 Claude 可以自由执行 bash 命令、读写文件等。如果你不放心，可以只把必要的 Channel 回复工具加入 allow 列表，其他保持默认。但要做好偶尔卡住的心理准备——这时候如果你有第二个 session，可以让它去帮忙 allow。

## 常见问题

见 [Troubleshooting](docs/troubleshooting.md)

## 项目和引用

- [Claude Code](https://github.com/anthropics/claude-code) - Anthropic 官方 CLI
- [claude-code-telegram](https://github.com/RichardAtCT/claude-code-telegram) - Telegram Bot（API 方案）
- [Memos](https://github.com/usememos/memos) - 轻量级笔记/记忆系统
- [claude-code-wechat-channel](https://github.com/Johnixr/claude-code-wechat-channel) - 微信频道插件

## License

MIT

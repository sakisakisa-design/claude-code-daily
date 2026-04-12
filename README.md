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
| Claude Max 订阅 | Opus 模型额度 | 是（或 API key） |
| CLAUDE.md | 行为规则和上下文 | 是 |
| Telegram Channel | Telegram 聊天 | 二选一 |
| WeChat Channel | 微信聊天 | 二选一 |
| Memos | 跨 session 长期记忆 | 推荐 |
| systemd + tmux | 后台常驻 + 自动重启 | 推荐 |

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

## 常见问题

见 [Troubleshooting](docs/troubleshooting.md)

## 项目和引用

- [Claude Code](https://github.com/anthropics/claude-code) - Anthropic 官方 CLI
- [Memos](https://github.com/usememos/memos) - 轻量级笔记/记忆系统
- [claude-code-wechat-channel](https://github.com/Johnixr/claude-code-wechat-channel) - 微信频道插件

## License

MIT

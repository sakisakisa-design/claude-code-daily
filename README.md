# Claude Code Daily

让 Claude Code 24 小时在线，通过 IM 随时对话，具备跨 session 长期记忆。

适用场景：日常助手、知识管理、项目协作、消息代理，或任何需要 agent 持续在线的场景。

## 架构

```
┌──────────────────────────────────────────────┐
│              Agent CLI                        │
│   Claude Code / Codex / Gemini / Kimi ...     │
├──────────────────────────────────────────────┤
│  CLAUDE.md（行为规则 / 工具配置 / 上下文）    │
│  Memory（auto memory 或 Memos）               │
├──────────────────────────────────────────────┤
│              cc-connect                       │
│  （进程内同时接多个 agent × 多个 IM）         │
├──────────┬──────────┬──────────┬─────────────┤
│ Telegram │  微信    │ Discord  │ 飞书/Slack  │
│          │          │          │  /QQ...     │
└──────────┴──────────┴──────────┴─────────────┘
                     ↓
              用户手机 / 桌面端
```

运行环境：Linux 服务器或 Mac mini，需要 24 小时在线。

## 组件

| 组件 | 用途 | 必选 |
|------|------|------|
| Claude Code CLI（或其他 agent CLI）| 跑模型 | 是 |
| Claude 订阅 或 API key | 二选一 | 是 |
| CLAUDE.md | 行为规则和上下文 | 是 |
| cc-connect | IM ↔ agent 桥接 | 是 |
| Memos | 跨 session 长期记忆 | 推荐 |
| systemd + tmux | 后台常驻 + 自动重启 | 推荐 |

cc-connect 支持的 agent（`[projects.agent.type]`）：`claudecode`、`codex`、`cursor`、`gemini`、`qoder`、`opencode`、`kimi`、`iflow`、任何 ACP 协议兼容的 agent。

支持的 IM 平台（`[[projects.platforms]]`）：Telegram、微信个人号（ilink）、企业微信、Discord、Slack、飞书/Lark、钉钉、LINE、微博、QQ（NapCat/OneBot）、QQ 官方 bot。

## 快速开始

### 1. 安装 Claude Code

```bash
# Node.js v18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo bash -
sudo apt-get install -y nodejs

npm install -g @anthropic-ai/claude-code
claude auth login
```

### 2. 工作区 + CLAUDE.md

```bash
mkdir -p ~/claude-workspace
cd ~/claude-workspace
```

在 `~/claude-workspace/CLAUDE.md` 里定义 Claude 的行为规则、输出风格、可用工具。参考 [examples/CLAUDE.md.example](examples/CLAUDE.md.example)。

### 3. 接入 IM

见 [cc-connect 配置指南](docs/cc-connect-setup.md)。

### 4. 长期记忆（可选）

见 [Memos 配置指南](docs/memos-setup.md)。

### 5. 后台常驻

见 [后台运行指南](docs/background-running.md)。

## 权限

Claude Code 默认每次工具调用都要手动批准。无人值守场景下这会卡住。cc-connect 在 `[projects.agent.options].mode` 里统一控制，`bypassPermissions` 全放行、`default` 要 IM 里回"允许"、`auto` 由 Claude 判断，见 [cc-connect 配置指南](docs/cc-connect-setup.md#权限模式)。

## 常见问题

见 [troubleshooting](docs/troubleshooting.md)。

## 项目引用

- [Claude Code](https://github.com/anthropics/claude-code) — Anthropic 官方 CLI
- [cc-connect](https://github.com/chenhg5/cc-connect) — agent × IM 桥接器
- [Memos](https://github.com/usememos/memos) — 笔记/记忆系统

## License

MIT

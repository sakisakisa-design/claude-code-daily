# Codex 配置

Codex 可以替代 Claude Code 接入 cc-connect。整体链路不变：IM → cc-connect → Codex CLI → 你的工作区。

## 前置条件

- Node.js v18+
- ChatGPT Plus / Pro / Team / Enterprise 账号，或 OpenAI API key
- 已经按 [cc-connect 配置指南](cc-connect-setup.md) 装好 cc-connect

## 1. 安装和登录

```bash
npm install -g @openai/codex
codex login
codex login status
```

如果你用 API key：

```bash
printenv OPENAI_API_KEY | codex login --with-api-key
```

先在服务器本机跑一次：

```bash
codex exec --cd ~/claude-workspace --skip-git-repo-check "用一句话回复：Codex 已连接"
```

这一步能跑通，再接 cc-connect。

## 2. 准备 AGENTS.md

Codex 会读取工作区里的 `AGENTS.md`。把你的长期行为规则、输出风格、记忆工具说明写进去。

在这个仓库根目录执行：

```bash
mkdir -p ~/claude-workspace
cp examples/AGENTS.md.example ~/claude-workspace/AGENTS.md
```

如果同一个工作区也给 Claude Code 用，可以同时保留 `CLAUDE.md` 和 `AGENTS.md`。

## 3. cc-connect 配置

把 `[projects.agent]` 改成 Codex：

```toml
[[projects]]
name = "codex-daily"
admin_from = "${ALLOWED_USERS}"
reset_on_idle_mins = 0
show_context_indicator = false
reply_footer = false
inject_sender = false

[projects.agent]
type = "codex"

[projects.agent.options]
work_dir = "${APPROVED_DIRECTORY}"
mode = "full-auto"
model = "gpt-5.3-codex"
reasoning_effort = "medium"

[[projects.platforms]]
type = "telegram"

[projects.platforms.options]
token = "${TELEGRAM_BOT_TOKEN}"
allow_from = "${ALLOWED_USERS}"
```

`mode` 可选值：

| mode | 行为 |
|---|---|
| `suggest` | 每次工具调用都要确认，最安全 |
| `auto-edit` | 自动批准文件编辑，shell 仍受限 |
| `full-auto` | 自动执行，保留工作区沙箱 |
| `yolo` | 跳过审批和沙箱，只适合隔离环境 |

24 小时在线建议用 `full-auto`，不要直接给生产机全盘权限。只有你把工作区、密钥、Docker 权限都隔离好了，才用 `yolo`。

## 4. 环境变量

`~/.cc-connect/env` 至少要有：

```bash
TELEGRAM_BOT_TOKEN=从_BotFather_复制
ALLOWED_USERS=你的_Telegram_user_id
APPROVED_DIRECTORY=/home/ubuntu/claude-workspace
```

如果你不用 ChatGPT 登录，而是用 API key：

```bash
OPENAI_API_KEY=sk-xxx
# 可选：第三方 OpenAI 兼容网关
OPENAI_BASE_URL=https://example.com/v1
```

## 5. 接入 memo-mcp

部署好 README 里的 memo-mcp 后，给 Codex 加 MCP：

```bash
codex mcp add memo-kb --url https://<你的项目名>.<your-subdomain>.workers.dev/mcp
```

如果 Worker 设置了 `API_KEY` secret：

```bash
codex mcp add memo-kb --url 'https://<你的项目名>.<your-subdomain>.workers.dev/mcp?token=你的token'
```

也可以手写 `~/.codex/config.toml`：

```toml
[mcp_servers.memo-kb]
url = "https://<你的项目名>.<your-subdomain>.workers.dev/mcp?token=你的token"
```

然后重启 cc-connect。

## 6. 常见坑

- cc-connect 找不到 Codex：确认 `codex` 在 systemd 的 `PATH` 里，必要时在 `start.sh` 加 `export PATH="$HOME/.npm-global/bin:/usr/local/bin:/usr/bin:$PATH"`。
- `AGENTS.md` 没生效：确认 `work_dir` 指向的就是 `AGENTS.md` 所在目录。
- 每次回复都像新会话：确认 cc-connect 日志里没有反复创建失败，Codex 会用 `codex exec resume` 续同一个 thread。
- 工具调用卡住：`suggest` 会等待确认，常驻 bot 改成 `full-auto`。
- API key 没生效：systemd 不读你的交互 shell 环境，把变量写进 `~/.cc-connect/env`。

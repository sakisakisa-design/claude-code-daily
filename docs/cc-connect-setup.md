# 聊天通道配置（cc-connect）

[cc-connect](https://github.com/chenhg5/cc-connect) 是一个 Go 写的桥接器，把本地 agent CLI（Claude Code、Codex、Cursor、Gemini、Kimi 等）接到各种 IM 平台（Telegram、微信、Discord、Slack、飞书、钉钉、QQ 等）。一个进程可以同时跑多个 project，每个 project 绑定一组 agent × 平台。

本指南用它接 Claude Code 到 Telegram 为例。换成其他 IM 只是替换 `[[projects.platforms]]` 段落，其他不变；接微信、Discord、飞书参考 cc-connect 自己的 [config.example.toml](https://github.com/chenhg5/cc-connect/blob/main/config.example.toml)。

## 前置条件

- 已安装 Claude Code CLI 并登录
- 如果接 Codex，已安装 Codex CLI 并登录，见 [codex-setup.md](codex-setup.md)
- 对应平台的 bot 凭证（Telegram 去 @BotFather `/newbot`）

## 1. 安装

Linux arm64 / amd64：

```bash
curl -sL https://github.com/chenhg5/cc-connect/releases/latest/download/cc-connect-v1.3.2-linux-amd64.tar.gz | tar -xz
# arm64 换成 cc-connect-v1.3.2-linux-arm64.tar.gz
mv cc-connect-v1.3.2-linux-amd64 ~/cc-connect/cc-connect
chmod +x ~/cc-connect/cc-connect
```

其他平台（Mac、Windows）去 [releases](https://github.com/chenhg5/cc-connect/releases) 页面选对应包。

## 2. 配置

`~/.cc-connect/config.toml`：

```toml
language = "zh"
data_dir = "/home/ubuntu/.cc-connect/data"

[log]
level = "info"

# 关掉流式预览（让回复作为整段/多段消息到达，而不是边改边推）
[stream_preview]
enabled = false

[[projects]]
name = "default"
admin_from = "${ALLOWED_USERS}"    # 特权命令授权的 user id
reset_on_idle_mins = 0
show_context_indicator = false     # 关掉消息末尾的 [ctx: ~N%]
reply_footer = false               # 关掉 Codex 风格 footer
inject_sender = false

[projects.agent]
type = "claudecode"

[projects.agent.options]
work_dir = "${APPROVED_DIRECTORY}"
mode = "bypassPermissions"         # 无人值守用；见下方权限说明

[[projects.platforms]]
type = "telegram"

[projects.platforms.options]
token = "${TELEGRAM_BOT_TOKEN}"
allow_from = "${ALLOWED_USERS}"

# 可选：Web 管理面板，端口 9820，token 登录
# [management]
# enabled = true
# port = 9820
# token = "长的随机字符串"
```

`chmod 600 ~/.cc-connect/config.toml`。

配置里用 `${VAR}` 引环境变量，另存 `~/.cc-connect/env`：

```
TELEGRAM_BOT_TOKEN=从_BotFather_复制
ALLOWED_USERS=你的_Telegram_user_id
APPROVED_DIRECTORY=/home/ubuntu/claude-workspace
```

`chmod 600 ~/.cc-connect/env`。

## 3. 启动

`~/cc-connect/start.sh`：

```bash
#!/usr/bin/env bash
set -a
. $HOME/.cc-connect/env
set +a
exec $HOME/cc-connect/cc-connect --config $HOME/.cc-connect/config.toml
```

`chmod +x ~/cc-connect/start.sh`，直接跑 `./start.sh` 测试。看到 `telegram: connected bot=xxx` 和 `platform ready` 就通了。去 Telegram 给 bot 发 `/whoami` 验证。

后台常驻见 [background-running.md](background-running.md)。

## 权限模式

下面是 Claude Code 的权限模式。

`[projects.agent.options].mode` 取值：

| mode | 行为 |
|---|---|
| `default` | 每次工具调用都要在 IM 里回"允许"/`allow` |
| `acceptEdits` | 文件编辑自动放行，其他要确认 |
| `plan` | 只做规划，不执行 |
| `auto` | Claude 自己判断 |
| `bypassPermissions` | 全部自动放行 |
| `dontAsk` | 未预授权的一律拒绝 |

24 小时无人值守选 `bypassPermissions`——它等于给 Claude 对该 `work_dir` 下的一切放行。如果你不放心，用 `default` + `allowed_tools` 白名单。

如果 `[projects.agent].type = "codex"`，`mode` 用 Codex 的四档：

| mode | 行为 |
|---|---|
| `suggest` | 每次工具调用都要确认 |
| `auto-edit` | 自动批准文件编辑，shell 仍受限 |
| `full-auto` | 自动执行，保留工作区沙箱 |
| `yolo` | 跳过审批和沙箱 |

Codex 常驻建议先用 `full-auto`。完整示例见 [codex-setup.md](codex-setup.md)。

## 常用命令（在 IM 里发）

- `/new` — 新建 session
- `/list` `/switch` — 会话历史
- `/whoami` `/status` — 看 user id / 会话状态
- `/mode` — 切权限模式
- `/help` — 完整列表

## 消息分段（可选补丁）

cc-connect 默认把 agent 的一次 reply 作为一条 Telegram 消息发出（关了 `stream_preview` 后就是一整条）。想把长回复拆成多条短消息模拟打字的，改 Go 源码：

`platform/telegram/telegram.go` 的 `Reply` 和 `Send` 函数改成调用一个分段 helper：

```go
// 按空行切段；含 ``` 代码块整段发
func splitForChat(text string) []string {
    s := strings.TrimSpace(text)
    if s == "" {
        return nil
    }
    if strings.Contains(s, "```") {
        return []string{s}
    }
    parts := strings.Split(s, "\n\n")
    out := make([]string, 0, len(parts))
    for _, p := range parts {
        if p = strings.TrimSpace(p); p != "" {
            out = append(out, p)
        }
    }
    if len(out) == 0 {
        return []string{s}
    }
    return out
}

func (p *Platform) sendChunked(ctx context.Context, bot telegramBot,
    chatID int64, threadID int, replyToID int, content string) error {
    chunks := splitForChat(content)
    for i, ch := range chunks {
        if i > 0 {
            time.Sleep(250 * time.Millisecond)
        }
        html := core.MarkdownToSimpleHTML(ch)
        params := &tgbot.SendMessageParams{
            ChatID: chatID, MessageThreadID: threadID,
            Text: html, ParseMode: models.ParseModeHTML,
        }
        if i == 0 && replyToID != 0 {
            params.ReplyParameters = &models.ReplyParameters{MessageID: replyToID}
        }
        if _, err := bot.SendMessage(ctx, params); err != nil {
            if strings.Contains(err.Error(), "can't parse") {
                params.Text, params.ParseMode = ch, ""
                if _, err2 := bot.SendMessage(ctx, params); err2 != nil {
                    return fmt.Errorf("telegram: send: %w", err2)
                }
                continue
            }
            return fmt.Errorf("telegram: send: %w", err)
        }
    }
    return nil
}
```

`Reply()` / `Send()` 原本的 `bot.SendMessage(...)` 改成 `return p.sendChunked(ctx, bot, rc.chatID, rc.threadID, rc.messageID /* Reply */ / 0 /* Send */, content)`。

然后 `make build` 重编二进制替换。

代价：升级 cc-connect 版本要重新 rebase 这个 patch。

要分段效果更自然，还可以在 `CLAUDE.md` 里让 Claude 用空行自己分段，比如：

```
输出时按意义用换行分段，每段一个完整意思。别把一句话硬拆两段。技术输出整段发。
```

这样 Claude 产生段落分隔，cc-connect 按段发。

## 代理（国内服务器）

cc-connect 本身没有独立代理配置，靠环境变量：

```bash
# 在 start.sh 里
export HTTPS_PROXY=http://127.0.0.1:7890
export HTTP_PROXY=http://127.0.0.1:7890
```

Discord 平台例外，`[projects.platforms.options]` 里有 `proxy` 字段。

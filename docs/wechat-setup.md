# 微信频道配置

通过 [claude-code-wechat-channel](https://github.com/Johnixr/claude-code-wechat-channel) 社区插件接入微信客服消息。

## 前置条件

- 已安装 Claude Code CLI
- 已安装 Node.js (v18+)
- 一个微信公众号 / 小程序的客服消息权限（需要企业认证或个人订阅号开通客服功能）

## 步骤

### 1. 安装插件

```bash
npm install -g claude-code-wechat-channel
```

验证安装：

```bash
npx claude-code-wechat-channel --help
```

如果提示 `npx: command not found`，确认 Node.js 已正确安装。

### 2. 配置 MCP Server

在工作区根目录创建 `.mcp.json`：

```json
{
  "mcpServers": {
    "wechat": {
      "command": "npx",
      "args": ["-y", "claude-code-wechat-channel", "start"]
    }
  }
}
```

### 3. 配置微信账号

首次启动时插件会引导你登录，或手动创建配置：

```bash
mkdir -p ~/.claude/channels/wechat
```

创建 `~/.claude/channels/wechat/account.json`：

```json
{
  "token": "你的客服消息token",
  "baseUrl": "https://ilinkai.weixin.qq.com",
  "accountId": "你的账号ID@im.bot",
  "userId": "用户OpenID@im.wechat",
  "savedAt": "2026-01-01T00:00:00Z"
}
```

具体参数从微信客服平台获取。

### 4. 启动

```bash
cd ~/claude-workspace
claude --model claude-opus-4-6 --dangerously-load-development-channels server:wechat
```

注意：`--dangerously-load-development-channels` 启动时会有确认提示，需要按 Enter 确认。

### 5. settings.json 配置

在对应的 Claude config 目录下的 `settings.json` 添加微信工具的自动授权：

```json
{
  "permissions": {
    "allow": [
      "mcp__wechat__wechat_reply",
      "mcp__wechat__wechat_send_image"
    ]
  }
}
```

## 多 Session 运行（同时接 Telegram + 微信）

如果想同时运行 Telegram 和微信，需要两个独立的 Claude Code 实例：

1. **使用独立的 config 目录**：

```bash
# Session 1 (Telegram) - 使用默认 config
claude --channels plugin:telegram@claude-plugins-official

# Session 2 (WeChat) - 使用独立 config
CLAUDE_CONFIG_DIR=~/.claude-2 claude --dangerously-load-development-channels server:wechat
```

2. **使用独立的工作区**：

```bash
mkdir -p ~/claude-workspace    # Telegram
mkdir -p ~/claude-workspace-2  # WeChat
```

每个工作区放各自的 `CLAUDE.md` 和 `.mcp.json`。

## 注意事项

- **一个微信号只能接一个 bot**：目前微信客服消息的限制，一个微信账号只能绑定一个 Claude Code 实例
- 微信客服消息有 48 小时回复窗口限制，用户需在 48 小时内发过消息才能收到回复
- 图片发送使用 `wechat_send_image` 工具，需要提供本地文件绝对路径
- 微信不支持 markdown 格式，回复时应使用纯文本

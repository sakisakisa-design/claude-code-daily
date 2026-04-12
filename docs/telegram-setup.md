# Telegram 频道配置

Telegram 是 Claude Code 官方支持的 Channel，通过 plugin 加载，配置最简单。

## 前置条件

- 已安装 Claude Code CLI
- 一个 Telegram Bot Token（从 @BotFather 获取）

## 步骤

### 1. 创建 Telegram Bot

1. 打开 Telegram，搜索 `@BotFather`
2. 发送 `/newbot`
3. 按提示设置 bot 名称
4. 获取 Bot Token（格式：`123456789:ABCdef...`）
5. 保存好 Token

### 2. 配置 Channel

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

### 3. 配置访问控制

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

获取你的 Telegram user ID：给 `@userinfobot` 发消息即可。

### 4. 启动

```bash
claude --model claude-opus-4-6 --channels plugin:telegram@claude-plugins-official
```

### 5. 配对

首次使用时，在 Telegram 给你的 bot 发消息，终端会出现配对请求，输入 `/telegram:access` 批准。

## 代理设置（国内服务器必看）

如果服务器在国内或无法直连 Telegram API，需要配置代理。

### 方法 1：环境变量

在启动脚本或 systemd service 中添加：

```bash
export HTTPS_PROXY=http://127.0.0.1:7890
export HTTP_PROXY=http://127.0.0.1:7890
```

### 方法 2：系统级代理

确保代理软件（clash / v2ray 等）在 Claude Code 启动前运行。

### 常见症状

- bot 创建成功但收不到消息 → 大概率是代理问题
- 发消息后 Claude 无反应 → 检查 Telegram Channel 是否成功连接（看启动日志）
- 间歇性断连 → 代理不稳定，考虑更换节点

## settings.json 配置

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

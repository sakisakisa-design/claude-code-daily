# 常见问题排查

## bun 没有安装

**症状**：启动时报 `bun: command not found`，或某些 channel 插件无法加载。

**解决**：

```bash
curl -fsSL https://bun.sh/install | bash
source ~/.bashrc
bun --version
```

如果装了还是找不到，检查 PATH：

```bash
echo $PATH | grep bun
```

确保 `~/.bun/bin` 在 PATH 中。systemd service 中也要显式设置：

```ini
Environment="PATH=/home/ubuntu/.bun/bin:/home/ubuntu/.npm-global/bin:/usr/local/bin:/usr/bin:/bin"
```

## Telegram Channel 收不到消息

### 检查 1：代理配置

国内服务器必须配代理才能连 Telegram API。

```bash
# 测试是否能连 Telegram
curl -x http://127.0.0.1:7890 https://api.telegram.org/bot你的TOKEN/getMe
```

如果不通，配置代理：

```bash
# 在 launcher 脚本或 systemd service 中添加
export HTTPS_PROXY=http://127.0.0.1:7890
export HTTP_PROXY=http://127.0.0.1:7890
```

### 检查 2：Bot Token 是否正确

```bash
cat ~/.claude/channels/telegram/.env
```

验证 Token：

```bash
curl https://api.telegram.org/bot你的TOKEN/getMe
```

### 检查 3：Channel 插件是否启用

查看 `~/.claude/settings.json`：

```json
{
  "enabledPlugins": {
    "telegram@claude-plugins-official": true
  }
}
```

如果 plugin 显示 disabled，在 Claude Code 中运行 `/plugins` 重新 enable。

### 检查 4：access.json 配置

```bash
cat ~/.claude/channels/telegram/access.json
```

确认你的 user ID 在 `allowFrom` 列表中。

## WeChat Channel 连接问题

### Token 过期

微信客服消息的 token 可能过期，需要重新获取。检查：

```bash
cat ~/.claude/channels/wechat/account.json
```

### npx 找不到包

```bash
# 确认包已安装
npm list -g claude-code-wechat-channel

# 如果没有
npm install -g claude-code-wechat-channel
```

## Claude Code 启动后立刻退出

### 检查 1：认证状态

```bash
claude auth status
```

如果未登录：

```bash
claude auth login
```

### 检查 2：tmux 是否安装

```bash
tmux -V
```

没装就装：

```bash
# Ubuntu/Debian
sudo apt-get install -y tmux

# Mac
brew install tmux
```

### 检查 3：查看日志

```bash
cat /tmp/claude-launcher.log
```

## systemd 服务启动失败

```bash
# 查看详细错误
sudo journalctl -u claude-code.service -n 50 --no-pager

# 常见问题：权限
ls -la ~/claude-workspace/scripts/claude-code-launcher.sh
# 应该有 x 权限，没有就加：
chmod +x ~/claude-workspace/scripts/claude-code-launcher.sh
```

## CLAUDE.md 没有生效

Claude Code 只在工作区根目录自动加载 `CLAUDE.md`。检查：

1. 文件名是否正确（大写：`CLAUDE.md`，不是 `claude.md`）
2. 文件是否在工作区根目录
3. systemd service 的 `WorkingDirectory` 是否指向正确的工作区

```bash
ls -la ~/claude-workspace/CLAUDE.md
```

## Memos 连接失败

### Docker 容器没运行

```bash
docker ps | grep memos

# 如果没有
docker start memos

# 如果容器不存在，重新创建
docker run -d --name memos --restart always -p 5230:5230 -v ~/memos-data:/var/opt/memos neosmemo/memos:stable
```

### Token 无效

在 Memos Web UI (http://localhost:5230) → Settings → Access Tokens 检查 token 是否有效。

### 测试连接

```bash
curl -s http://localhost:5230/api/v1/memos?pageSize=1 \
  -H "Authorization: Bearer 你的TOKEN" \
  -H "Accept: application/json"
```

## 多实例冲突

同时运行多个 Claude Code 实例时，需要确保：

1. **独立的 config 目录**：第二个实例用 `CLAUDE_CONFIG_DIR=~/.claude-2`
2. **独立的 tmux socket**：不同的 `/tmp/tmux-claude-N/default`
3. **独立的工作区**：不同的 `WorkingDirectory`
4. **独立的 systemd service 文件**：不同的 service name

## Mac mini 特有问题

### tmux 断连

Mac mini 休眠后 tmux session 可能断开：

- 系统设置 → 节能 → 关闭「自动休眠」
- 终端执行：`sudo pmset -a disablesleep 1`

### Docker 性能

Mac 上 Docker Desktop 占用资源较多。如果只跑 Memos，可以考虑直接用 Memos 的二进制安装，不走 Docker。

### PATH 问题

Mac 的默认 PATH 和 Linux 不同，launcher 脚本中需要调整：

```bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.bun/bin:$PATH"
```

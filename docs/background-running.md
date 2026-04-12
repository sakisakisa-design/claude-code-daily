# 后台运行与自动重启

让 Claude Code 在服务器上 24 小时运行，断开 SSH 也不中断。

## 架构

```
systemd timer (每天 4:00 重启)
    ↓
systemd service → launcher.sh → tmux session → claude CLI
```

- **systemd**：管理进程生命周期，崩溃自动重启
- **tmux**：提供虚拟终端，让 Claude Code 的交互式界面能在后台运行
- **launcher 脚本**：衔接 systemd 和 tmux，处理启动逻辑

## 1. 创建启动脚本

```bash
mkdir -p ~/claude-workspace/scripts
```

创建 `~/claude-workspace/scripts/claude-code-launcher.sh`：

```bash
#!/bin/bash
# Claude Code 启动脚本

TMUX_SOCK="/tmp/tmux-claude/default"
TMUX_SESSION="claude-code"
LOG_FILE="/tmp/claude-launcher.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"; }

# 防止 tmux 嵌套冲突
unset TMUX

log "=== Claude Code Launcher ==="

mkdir -p /tmp/tmux-claude
chmod 700 /tmp/tmux-claude

# 清理旧 session
tmux -S "$TMUX_SOCK" kill-session -t "$TMUX_SESSION" 2>/dev/null
sleep 1

# 设置环境
export PATH="$HOME/.bun/bin:$HOME/.npm-global/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export HOME="/home/ubuntu"

log "Starting Claude Code..."

# 启动 Claude Code（根据你的 channel 选择参数）
# Telegram:
tmux -S "$TMUX_SOCK" new-session -d -s "$TMUX_SESSION" -c ~/claude-workspace \
  claude --model claude-opus-4-6 --effort max --channels plugin:telegram@claude-plugins-official

# 或 WeChat:
# tmux -S "$TMUX_SOCK" new-session -d -s "$TMUX_SESSION" -c ~/claude-workspace \
#   claude --model claude-opus-4-6 --effort max --dangerously-load-development-channels server:wechat

sleep 2

if tmux -S "$TMUX_SOCK" has-session -t "$TMUX_SESSION" 2>/dev/null; then
    log "Session started successfully"
else
    log "WARNING: Session did not start"
fi

# 保持脚本运行直到 tmux session 结束
while tmux -S "$TMUX_SOCK" has-session -t "$TMUX_SESSION" 2>/dev/null; do
    sleep 5
done

log "Session ended, exiting"
exit 0
```

```bash
chmod +x ~/claude-workspace/scripts/claude-code-launcher.sh
```

### WeChat 特殊处理

如果用微信 channel，启动时有确认提示需要自动按 Enter：

```bash
# 在 tmux new-session 之后添加：
sleep 5
tmux -S "$TMUX_SOCK" send-keys -t "$TMUX_SESSION" Enter
```

## 2. 创建 systemd 服务

```bash
sudo tee /etc/systemd/system/claude-code.service << 'EOF'
[Unit]
Description=Claude Code Daily
After=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
Environment="PATH=/home/ubuntu/.bun/bin:/home/ubuntu/.npm-global/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="HOME=/home/ubuntu"
WorkingDirectory=/home/ubuntu/claude-workspace

ExecStartPre=/bin/mkdir -p /tmp/tmux-claude
ExecStartPre=/bin/chmod 700 /tmp/tmux-claude
ExecStart=/home/ubuntu/claude-workspace/scripts/claude-code-launcher.sh

ExecStop=/bin/sh -c 'tmux -S /tmp/tmux-claude/default send-keys -t claude-code C-c 2>/dev/null || true'
ExecStop=/bin/sleep 1
ExecStop=/bin/sh -c 'tmux -S /tmp/tmux-claude/default kill-session -t claude-code 2>/dev/null || true'

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

启用并启动：

```bash
sudo systemctl daemon-reload
sudo systemctl enable claude-code.service
sudo systemctl start claude-code.service
```

查看状态：

```bash
sudo systemctl status claude-code.service
```

查看日志：

```bash
cat /tmp/claude-launcher.log
```

## 3. 创建每日自动重启

Claude Code 长时间运行后 context 会越来越长，定时重启能保持状态清洁。

### 创建重启服务

```bash
sudo tee /etc/systemd/system/claude-restart-daily.service << 'EOF'
[Unit]
Description=Daily restart of Claude Code sessions

[Service]
Type=oneshot
User=root
ExecStart=/bin/bash -c 'systemctl restart claude-code.service && echo "$(date) Session restarted" >> /tmp/claude-restart-daily.log'
EOF
```

### 创建定时器

```bash
sudo tee /etc/systemd/system/claude-restart-daily.timer << 'EOF'
[Unit]
Description=Restart Claude Code sessions daily at 4:00 AM

[Timer]
OnCalendar=*-*-* 04:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF
```

启用：

```bash
sudo systemctl daemon-reload
sudo systemctl enable claude-restart-daily.timer
sudo systemctl start claude-restart-daily.timer
```

验证定时器状态：

```bash
sudo systemctl list-timers | grep claude
```

## 4. 日常运维命令

```bash
# 查看 Claude 是否在运行
sudo systemctl status claude-code

# 手动重启
sudo systemctl restart claude-code

# 查看 Claude 的实时终端（可以交互）
tmux -S /tmp/tmux-claude/default attach -t claude-code

# 从 tmux 中退出（不杀进程）
# 按 Ctrl+B 然后按 D

# 查看启动日志
cat /tmp/claude-launcher.log

# 查看重启记录
cat /tmp/claude-restart-daily.log
```

## Mac mini 用户

Mac mini 没有 systemd，用 launchd 替代：

### 创建 plist

```bash
cat > ~/Library/LaunchAgents/com.claude.companion.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.claude.companion</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/你的用户名/claude-workspace/scripts/claude-code-launcher.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>/Users/你的用户名/claude-workspace</string>
    <key>StandardOutPath</key>
    <string>/tmp/claude-launcher.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/claude-launcher-error.log</string>
</dict>
</plist>
EOF
```

加载：

```bash
launchctl load ~/Library/LaunchAgents/com.claude.companion.plist
```

### Mac mini 注意事项

- tmux 可能需要通过 Homebrew 安装：`brew install tmux`
- bun 安装：`brew install oven-sh/bun/bun`
- 确保 Mac mini 不会自动休眠：系统设置 → 节能 → 阻止自动休眠
- 路径和 Linux 不同，launcher 脚本中的 PATH 需要调整

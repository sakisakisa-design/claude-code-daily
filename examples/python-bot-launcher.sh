#!/bin/bash
# Python Telegram Bot 启动脚本模板
# 用法：放到 ~/claude-workspace/scripts/ 目录下，chmod +x

TMUX_SOCK="/tmp/tmux-claude/default"
TMUX_SESSION="python-tg-bot"
LOG_FILE="/tmp/python-bot-launcher.log"
BOT_DIR="$HOME/claude-code-telegram"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"; }

unset TMUX

log "=== Python TG Bot Launcher ==="

mkdir -p /tmp/tmux-claude
chmod 700 /tmp/tmux-claude

tmux -S "$TMUX_SOCK" kill-session -t "$TMUX_SESSION" 2>/dev/null
sleep 1

export PATH="$HOME/.bun/bin:$HOME/.npm-global/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export HOME="/home/ubuntu"

# 如果使用兼容 API（中转站等），取消下面的注释并修改地址
# export ANTHROPIC_BASE_URL=http://127.0.0.1:3002

# 如果需要代理（国内服务器连 Telegram）
# export HTTPS_PROXY=http://127.0.0.1:7890
# export HTTP_PROXY=http://127.0.0.1:7890

log "Starting Python TG bot..."

tmux -S "$TMUX_SOCK" new-session -d -s "$TMUX_SESSION" -c "$BOT_DIR" \
  "cd $BOT_DIR && source venv/bin/activate && python -m src.main 2>&1 | tee -a /tmp/claude-tg-bot.log"

sleep 3

if tmux -S "$TMUX_SOCK" has-session -t "$TMUX_SESSION" 2>/dev/null; then
    log "Python TG bot started successfully"
else
    log "WARNING: Python TG bot did not start"
fi

while tmux -S "$TMUX_SOCK" has-session -t "$TMUX_SESSION" 2>/dev/null; do
    sleep 5
done

log "Python TG bot ended, exiting"
exit 0

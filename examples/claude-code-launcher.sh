#!/bin/bash
# Claude Code 启动脚本模板
# 用法：放到 ~/claude-workspace/scripts/ 目录下，chmod +x

TMUX_SOCK="/tmp/tmux-claude/default"
TMUX_SESSION="claude-code"
LOG_FILE="/tmp/claude-launcher.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"; }

unset TMUX

log "=== Claude Code Launcher ==="

mkdir -p /tmp/tmux-claude
chmod 700 /tmp/tmux-claude

tmux -S "$TMUX_SOCK" kill-session -t "$TMUX_SESSION" 2>/dev/null
sleep 1

export PATH="$HOME/.bun/bin:$HOME/.npm-global/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export HOME="/home/ubuntu"
# 如果需要代理（国内服务器连 Telegram 必须）：
# export HTTPS_PROXY=http://127.0.0.1:7890
# export HTTP_PROXY=http://127.0.0.1:7890

log "Starting Claude Code..."

# === 选择你的 Channel，取消对应注释 ===

# Telegram:
tmux -S "$TMUX_SOCK" new-session -d -s "$TMUX_SESSION" -c ~/claude-workspace \
  claude --model claude-opus-4-6 --effort max --channels plugin:telegram@claude-plugins-official

# WeChat:
# tmux -S "$TMUX_SOCK" new-session -d -s "$TMUX_SESSION" -c ~/claude-workspace \
#   claude --model claude-opus-4-6 --effort max --dangerously-load-development-channels server:wechat
# sleep 5
# tmux -S "$TMUX_SOCK" send-keys -t "$TMUX_SESSION" Enter  # 自动确认 WeChat 启动提示

sleep 2

if tmux -S "$TMUX_SOCK" has-session -t "$TMUX_SESSION" 2>/dev/null; then
    log "Session started successfully"
else
    log "WARNING: Session did not start"
fi

while tmux -S "$TMUX_SOCK" has-session -t "$TMUX_SESSION" 2>/dev/null; do
    sleep 5
done

log "Session ended, exiting"
exit 0

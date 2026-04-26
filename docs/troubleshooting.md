# 常见问题排查

## Telegram：`Conflict: terminated by other getUpdates request`

多个进程在用同一个 Bot Token 抢长轮询。Telegram 只允许一个客户端消费 updates。

排查：

```bash
ps -eo pid,etime,cmd | grep -iE "cc-connect|telegram|claude-plugins-official/telegram"
```

常见来源：

- 旧的 python bot 或官方 telegram plugin 还在跑 —— 停掉
- Claude Code 自己的 telegram plugin（`~/.claude/plugins/cache/claude-plugins-official/telegram`）被启用 —— 在 `work_dir/.claude/settings.json` 里把 `"telegram@claude-plugins-official"` 设为 `false`，或直接清空 `enabledPlugins`
- 同一台机上起了两个 cc-connect 拉同一个 token —— 合成一个 project

## 回复显示成"长流式预览 + 后续多条短消息"

`[stream_preview]` 还开着。在 `config.toml` 加：

```toml
[stream_preview]
enabled = false
```

重启 cc-connect。

## bot 收到消息后没有回复

1. 检查 agent 是否连上：日志里应该有 `agent ready` / `session spawned`
2. `[projects.agent.options].mode`：`default` 模式下 agent 每次工具调用都要 IM 里回"允许"，卡住就是在等你确认
3. 看 Claude Code 是否登录：`claude auth status`
4. `APPROVED_DIRECTORY` / `work_dir` 指向的目录存在且可写
5. 国内服务器：API 不通，配代理（见 [background-running.md](background-running.md#代理)）

## cc-connect 启动报 `instance lock` 或 `address already in use`

前一个实例没清干净。

```bash
ps aux | grep cc-connect
kill <pid>
rm -f ~/.cc-connect/.config.toml.lock
# 管理面板端口冲突时
ss -tlnp | grep 9820
```

或启动时加 `--force`：`cc-connect --force --config ~/.cc-connect/config.toml`。

## 管理面板 (9820) 打不开

- 检查 `[management].enabled = true` 且 `token` 已设
- `ss -tlnp | grep 9820` 确认在监听
- 云服务器需要在 VPC / Security List 放行 9820 入站
- 明文 HTTP，走公网建议套 HTTPS 或用 SSH 隧道：`ssh -L 9820:127.0.0.1:9820 server`

## CLAUDE.md 没生效

Claude Code 只在 `work_dir` 根目录自动加载 `CLAUDE.md`。

1. 文件名大写：`CLAUDE.md`
2. 路径是 `config.toml` 里 `work_dir` 指向的目录
3. 也可在 `~/.claude/CLAUDE.md` 放全局规则

## AGENTS.md 没生效

Codex 读取 `work_dir` 根目录和上级目录里的 `AGENTS.md`。

1. 文件名大写：`AGENTS.md`
2. 路径是 `config.toml` 里 `work_dir` 指向的目录，或它的上级目录
3. systemd 启动时确认 `APPROVED_DIRECTORY` 和你手动测试 Codex 的目录一致

## cc-connect 找不到 `codex`

systemd 的 `PATH` 通常比交互 shell 短。先查 Codex 位置：

```bash
command -v codex
```

然后在 `~/cc-connect/start.sh` 里加：

```bash
export PATH="$HOME/.npm-global/bin:/usr/local/bin:/usr/bin:$PATH"
```

重启 cc-connect。

## Codex 工具调用一直卡住

`mode = "suggest"` 会等待确认。24 小时 bot 改成：

```toml
[projects.agent.options]
mode = "full-auto"
```

如果你确定机器已经隔离，才用 `mode = "yolo"`。

## Memos 连接失败

Docker 容器状态：

```bash
docker ps | grep memos
docker start memos  # 已创建但没跑
# 首次创建：
docker run -d --name memos --restart always -p 5230:5230 -v ~/memos-data:/var/opt/memos neosmemo/memos:stable
```

Token：Memos Web UI (http://localhost:5230) → Settings → Access Tokens。

测试：

```bash
curl -s http://localhost:5230/api/v1/memos?pageSize=1 \
  -H "Authorization: Bearer 你的TOKEN"
```

## systemd service 起不来

```bash
journalctl -u cc-connect.service -n 50 --no-pager
```

常见原因：

- `start.sh` 没有 x 权限：`chmod +x ~/cc-connect/start.sh`
- `~/.cc-connect/env` 里变量名和 `config.toml` 里的 `${...}` 不一致
- `User=ubuntu` 但实际用户名不是 ubuntu

## Mac mini tmux / 休眠

- 关自动休眠：系统设置 → 节能，或 `sudo pmset -a disablesleep 1`
- bun/tmux 从 Homebrew 装：`brew install tmux oven-sh/bun/bun`
- `start.sh` 的 PATH 要加 `/opt/homebrew/bin`

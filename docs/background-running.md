# 后台运行与自动重启

让 cc-connect 在服务器上 24 小时运行，断开 SSH 不中断，崩溃自动重启，每天定时滚一次 session。

cc-connect 本身是单进程守护，不需要 tmux 包装。用 systemd 拉起就行。

## 1. systemd service

假设你已经按 [cc-connect-setup.md](cc-connect-setup.md) 配好了 `~/cc-connect/start.sh` 和 `~/.cc-connect/config.toml`。

```bash
sudo tee /etc/systemd/system/cc-connect.service < examples/cc-connect.service
# （或直接复制 examples/cc-connect.service 到 /etc/systemd/system/）

sudo systemctl daemon-reload
sudo systemctl enable --now cc-connect.service
```

查看状态和日志：

```bash
systemctl status cc-connect.service
journalctl -u cc-connect.service -n 100 -f
```

## 2. 每日自动重启

Claude Code 会话开得久了 context 越来越长，定时重启让它回到干净状态。

```bash
sudo cp examples/cc-connect-restart-daily.service /etc/systemd/system/
sudo cp examples/cc-connect-restart-daily.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cc-connect-restart-daily.timer

systemctl list-timers | grep cc-connect
```

## 3. 日常运维

```bash
# 启停重启
sudo systemctl {start,stop,restart} cc-connect.service

# 看日志（cc-connect 自己也写 stdout，journalctl 直接能看到）
journalctl -u cc-connect.service -f

# 看重启记录
cat /tmp/cc-connect-restart.log
```

用 cc-connect 自带的 daemon 子命令也行（它内部还是走 systemd）：

```bash
cc-connect daemon install      # 生成并安装 service
cc-connect daemon start
cc-connect daemon status
cc-connect daemon logs -f
```

## Mac mini

Mac 没有 systemd。cc-connect 的 `daemon install` 子命令自动识别 launchd，会生成 `~/Library/LaunchAgents/sh.cc-connect.daemon.plist`：

```bash
cc-connect daemon install
cc-connect daemon start
```

注意：

- 关闭自动休眠：系统设置 → 节能 → 阻止自动休眠，或 `sudo pmset -a disablesleep 1`
- 默认的 PATH 和 Linux 不同，`start.sh` 里需要包含 `/opt/homebrew/bin`

## 代理（国内服务器）

在 `~/cc-connect/start.sh` 里加：

```bash
export HTTPS_PROXY=http://127.0.0.1:7890
export HTTP_PROXY=http://127.0.0.1:7890
```

Discord 另有专门的 `proxy` 选项在 `[projects.platforms.options]` 里。

# Claude Code Daily

让 Claude Code / Codex 24 小时在线，通过 IM 随时对话，具备跨 session 长期记忆。

适用场景：日常助手、知识管理、项目协作、消息代理，或任何需要 agent 持续在线的场景。

> **2026-10 更新**
>
> - 长期记忆改推 [Aelios](https://github.com/wusaki0723/Aelios)。这个仓库原来的 memo-mcp 就是 Aelios 最早的样子，现在 memo-mcp 和 Memos 两套方案都停更了，教程挪进 `docs/` 留档，代码没删。
> - Claude Code 改用官方安装脚本，npm 装法官方已经标了弃用。
> - cc-connect 改用 npm 安装，原来钉死 v1.3.2 的下载链接已经失效。
> - 补了官方 Channels、Remote Control 和 cc-connect 的对比，加了一段 [Claude Projects](#claude-projects) 介绍，以及 2026-10-21 新 API 版本的注意事项。

## 架构

```
┌──────────────────────────────────────────────┐
│              Agent CLI                        │
│   Claude Code / Codex / Gemini / Kimi ...     │
├──────────────────────────────────────────────┤
│  CLAUDE.md（行为规则 / 工具配置 / 上下文）    │
│  Memory（Aelios 或 auto memory）              │
├──────────────────────────────────────────────┤
│              cc-connect                       │
│  （进程内同时接多个 agent × 多个 IM）         │
├──────────┬──────────┬──────────┬─────────────┤
│ Telegram │  微信    │ Discord  │ 飞书/Slack  │
│          │          │          │  /QQ...     │
└──────────┴──────────┴──────────┴─────────────┘
                     ↓
              用户手机 / 桌面端
```

运行环境：Linux 服务器或 Mac mini，需要 24 小时在线。

## 组件

| 组件 | 用途 | 必选 |
|------|------|------|
| Claude Code CLI 或 Codex CLI | 跑模型 | 是 |
| Claude 订阅 / ChatGPT 订阅 / API key | 三选一 | 是 |
| CLAUDE.md / AGENTS.md | 行为规则和上下文 | 是 |
| cc-connect | IM ↔ agent 桥接（只用 Claude Code 的也可以看看官方 Channels，见下一节） | 是 |
| [Aelios](https://github.com/wusaki0723/Aelios) | 跨 session、跨客户端的长期记忆，跑在你自己的 Cloudflare 上 | 推荐 |
| systemd（Mac 用 launchd） | 后台常驻 + 自动重启 | 推荐 |
| Memos / memo-mcp | 旧的记忆方案，已停更，只留档 | 否 |

cc-connect 支持的 agent（`[projects.agent].type`）：`claudecode`、`codex`、`cursor`、`gemini`、`copilot`、`pi`、`qoder`、`opencode`、`kimi`、`iflow`，以及任何 ACP 协议兼容的 agent。

支持的 IM 平台（`[[projects.platforms]]`）：Telegram、微信个人号（ilink）、企业微信、Discord、Slack、飞书/Lark、钉钉、LINE、微博、QQ（NapCat/OneBot）、QQ 官方 bot、Matrix、Google Chat 等，完整列表看 cc-connect 的 [config.example.toml](https://github.com/chenhg5/cc-connect/blob/main/config.example.toml)。

## 官方的同类功能

Claude 官方现在也有几样跟 cc-connect 同类的东西，按需要挑：

| 方案 | 是什么 | 适合 |
|------|--------|------|
| cc-connect | 第三方桥接器，一个进程接多个 agent × 多个 IM | 要接微信、飞书、QQ 这类国内 IM，或者要同时挂 Codex 等别家 agent |
| [Channels](https://code.claude.com/docs/en/channels)（研究预览） | 官方插件，把 Telegram / Discord / iMessage 的消息推进一个正在跑的 Claude Code 会话，回复也从原渠道发回去 | 只用 Claude Code，只用这三个 IM |
| [Remote Control](https://code.claude.com/docs/en/remote-control) | 用手机上的 Claude App 或 claude.ai/code 直接操作电脑上的 Claude Code 会话 | 不需要 IM，用官方 App 就够了 |
| [Claude Projects](#claude-projects)（公开测试） | 官方托管的「一个常驻主聊 + 一堆干活的线程」，跑在云端，带项目记忆 | 不想自己维护服务器，事情跨好几天、几条线一起推 |

几个要注意的地方：

- Channels 要用 claude.ai 账号或 Console API key 登录，插件要先装 [Bun](https://bun.sh)，启动时加参数，比如 `claude --channels plugin:telegram@claude-plugins-official`。会话关了就收不到消息，所以要常驻一样得配 systemd 或 tmux。
- Remote Control 只认订阅登录（Pro / Max / Team / Enterprise），不支持 API key；`ANTHROPIC_BASE_URL` 指向别的地址（网关、代理）时也用不了。
- cc-connect 和官方 Telegram 插件不要用同一个 bot token，两边会抢消息，见 [troubleshooting](docs/troubleshooting.md)。

### Claude Projects

[Projects](https://code.claude.com/docs/en/claude-projects) 是 claude.ai/code 里新出的玩法，想做的事跟这个仓库很像：一个一直在线、记得来龙去脉的 Claude，你随时丢活给它。区别是它全部由官方托管，不用自己搭服务器。

它是这样组织的：

- **一个常驻的主聊**：你在项目里说的每句话先到它这里。它负责回话、派活、记事，小问题当场答，要动手的活交给线程。
- **每件活开一个线程**：线程是独立的云端会话，有自己的上下文和工具（命令行、读写文件、GitHub 仓库和 PR、你 claude.ai 账号上的 MCP 连接器），干完把结论报回主聊。几个线程可以同时跑，关了电脑云端线程也照样跑。
- **项目记忆和项目说明**：要求、决定、踩过的坑写进项目记忆（一个 `MEMORY.md` 索引加若干小文件），每个新线程开工先读；项目说明（最多 16000 字）每个线程都会带上。
- **手机上就能用**：claude.ai/code、桌面 App 的 Code 页、Claude 手机 App 都能进。Overview 里看哪些线程干完了、哪些 PR 能审、哪个在等你回话。
- **要用本机的东西时**：让某个线程通过 Remote Control 跑在你自己的电脑上（电脑得开着，`claude remote-control` 或桌面 App 得开着），其他线程照样在云端。

用下来的感受：重活都在线程里烧，主聊只收结论，所以主聊能聊很久都不卡；反过来，查一行代码也常常要开个线程、再点进去看结果，只想快问快答会嫌慢。适合跨好几天、几条线同时推、需要有人替你记住来龙去脉的事。

跟本仓库这套比：

| | 本仓库（cc-connect + 自己的机器） | Claude Projects |
|------|------|------|
| 跑在哪 | 你自己的服务器或 Mac mini | Anthropic 的云端，个别线程可以挂到本机 |
| 从哪聊 | Telegram、微信、飞书等 IM | 官方网页、桌面 App、手机 App |
| 记忆 | Aelios、CLAUDE.md，自己管 | 官方的项目记忆；线程里也能用 Aelios 这类 claude.ai 连接器 |
| 模型 | Claude Code、Codex、Gemini 等都行 | 只有 Claude |
| 计费 | 订阅或 API 都行 | 只走 Pro / Max 订阅额度，几个线程一起跑，比单个会话用得快 |
| 谁能用 | 谁都能搭 | Pro / Max 公开测试，逐步放开；侧栏没有 Projects 就是还没轮到，可以[排队](https://claude.com/form/projects)；Team / Enterprise 暂时没有 |

不想维护服务器、也不需要接国内 IM 的，直接用 Projects 更省事。要接微信飞书、要挂别家模型、要数据全在自己手里的，还是用这套。

## 给 AI / Agent 的阅读入口

如果你把这个仓库丢给 Claude Code、Codex、Cursor、Gemini CLI 或其他 agent，让它按仓库帮你部署，优先读这些文件：

1. `README.md`：整体架构、Aelios 长期记忆怎么接
2. `docs/cc-connect-setup.md`：IM 桥接配置
3. `docs/codex-setup.md`：Codex CLI 接入 cc-connect
4. `docs/background-running.md`：systemd / launchd 常驻
5. `docs/troubleshooting.md`：常见故障

`docs/memo-mcp.md` 和 `docs/memos-setup.md` 是停更的旧方案，新部署不用看。

目标是跑通一条链路：`IM → cc-connect → Agent CLI → 工作区规则文件 → 长期记忆（Aelios）`。

## 快速开始

### 1. 安装 Agent CLI

Claude Code 路线：

```bash
# 官方安装脚本，装到 ~/.local/bin/claude，之后自动更新
curl -fsSL https://claude.ai/install.sh | bash
claude auth login
```

Mac 也可以 `brew install --cask claude-code`。原来的 `npm install -g @anthropic-ai/claude-code` 官方已经标了弃用，以前用 npm 装的，可以先 `npm uninstall -g @anthropic-ai/claude-code` 再跑上面的脚本。装好后跑一次 `claude doctor` 看安装是否正常。

systemd 里跑的时候 `PATH` 要包含 `~/.local/bin`，[examples/cc-connect.service](examples/cc-connect.service) 已经加上了。

Codex 路线：

```bash
npm install -g @openai/codex
codex login
```

### 2. 工作区 + 规则文件

```bash
mkdir -p ~/claude-workspace
cd ~/claude-workspace
```

Claude Code 用 `~/claude-workspace/CLAUDE.md` 定义行为规则、输出风格、可用工具。参考 [examples/CLAUDE.md.example](examples/CLAUDE.md.example)。

Codex 用 `~/claude-workspace/AGENTS.md` 定义同类规则。参考 [examples/AGENTS.md.example](examples/AGENTS.md.example)。

Codex 接入细节见 [Codex 配置指南](docs/codex-setup.md)。

### 3. 接入 IM

见 [cc-connect 配置指南](docs/cc-connect-setup.md)。

### 4. 长期记忆（推荐）

见下面的「[长期记忆：Aelios](#长期记忆aelios)」。

### 5. 后台常驻

见 [后台运行指南](docs/background-running.md)。

## 长期记忆：Aelios

[Aelios](https://github.com/wusaki0723/Aelios) 是跑在你自己 Cloudflare 账号上的记忆网关。换窗口、换客户端、换模型，记忆都跟着走；有网页后台，记了什么都看得见，能改、能删、能撤回；夜里会自动把聊天整理成长期记忆。

部署照它的 README 做：先 Fork，再在 Cloudflare 后台导入你的 Fork，加一个 `CHATBOX_API_KEY`，三步。装好后有两种接法。

### 订阅登录（Pro / Max）：接 MCP

```bash
claude mcp add --scope user --transport http aelios "https://<Worker 地址>/mcp?token=<CHATBOX_API_KEY>"
```

`--scope user` 让所有目录的会话都能用，cc-connect 在 `work_dir` 里起的会话也包括在内。重启后 `/mcp` 里能看到 `aelios`。

模型不会自己想起来用记忆，在工作区的 `CLAUDE.md` 里写一段（Aelios README 里给的原话）：

```markdown
## 长期记忆

我给你接了 Aelios 记忆连接器，那是你对我的长期记忆。每个新对话先调 wake_up 再回我；我提到以前的人和事，或者你要猜我的事之前，先 recall；我说了新的事、改了主意、许了约定，当场 remember；聊得差不多了调 log_conversation。
```

想每条消息自动召回、对话自动写回，不靠模型自己调工具，用 Aelios 仓库里的 [Claude Code Hook](https://github.com/wusaki0723/Aelios/tree/main/integrations/claude-code)。

Codex 一样接 MCP：

```bash
codex mcp add aelios --url 'https://<Worker 地址>/mcp?token=<CHATBOX_API_KEY>'
```

### API 计费：把请求指到 Aelios 网关

在 `~/.cc-connect/env`（或你的 shell）里把 `ANTHROPIC_BASE_URL` 指到 Aelios 的助手地址，`ANTHROPIC_API_KEY` 填 `CHATBOX_API_KEY`，具体地址和模型名写法看 Aelios README 第 3 步。这样每句对话都经过 Aelios，自动记、自动召回，不用模型自己调工具。

代价是请求走你在 Cloudflare AI Gateway 存的 key 或 credits 计费，不走订阅额度；这种设置下 Remote Control 和 Artifacts 也用不了。

### 以前装过 memo-mcp 的

Aelios 默认也用名叫 `memo-kb` 的 Vectorize 索引，但要 1024 维，memo-mcp 建的是 768 维。同一个 Cloudflare 账号里旧索引有数据时，Aelios 的部署会停下来报错，不会替你删。两个办法选一个：

- **给 Aelios 换个索引名**：在 Aelios 那个 Worker 的 **Settings → Build → Build Variables and Secrets** 里加 `CMP_VECTORIZE_NAME`，填一个新名字（比如 `aelios-kb`），再重新部署。旧的 memo-mcp 照常能用。
- **旧记忆不要了**：`npx wrangler vectorize delete memo-kb`。删了找不回来，先想清楚。

旧记忆想搬过去：memo-mcp 没有导出功能，可以让 Claude 用 `search_memory` 按主题把要紧的捞出来，整理成一行一条的列表，再到 Aelios 后台「更多 → 导入导出」里导入，导入时可以选直接写进库还是先进审核页。

旧教程留档：[docs/memo-mcp.md](docs/memo-mcp.md)、[docs/memos-setup.md](docs/memos-setup.md)，都不再更新。

## Claude API 接入

订阅（Pro / Max）走 `claude auth login` 就够了，下面是没订阅、想按量付费的几条路。

### 在 Cloudflare AI Gateway 买 Claude API

适合 Anthropic 直充不通、或想顺便拿 Gateway 的统计、缓存、限流能力的人。最低 10 美元起充，5% 手续费，价格官方价不加。拿到的 endpoint 和 `cfut_` token 可以喂给 Claude Code、Claude Desktop 或自己的脚本。

完整教程：[docs/cf-claude-api.md](docs/cf-claude-api.md)，含 prompt cache 命中坑（必须加 `cf-aig-skip-cache: true` 且 system 转数组带 `cache_control`）。

### Claude Desktop 接入第三方 API

Claude Desktop 自带 **Cowork on 3P** 模式，可以不登 Anthropic 账号、直接用 CF AI Gateway / Vertex / Bedrock / Foundry 跑。GUI 用户、被 ban 账号、或者公司统一用 Vertex 的场景适用。

完整教程：[docs/claude-desktop-3p.md](docs/claude-desktop-3p.md)，含个人路径（Apply locally）和企业 MDM 路径的入口区别。

### 2026-10-21 新 API 版本

Anthropic 在 2026-10-21 发了新的 API 版本（请求头 `anthropic-version: 2026-10-21`）。自己写脚本、反代的要注意：

- 请求里带 `temperature`、`top_p`、`top_k` 会直接 400，哪怕填的是默认值。
- `document` 块不能直接放在 assistant 消息里；user 消息里的 text 块不能带非空的 `citations`。
- 新版官方 SDK（Python 2.0、TypeScript 1.0 起）默认就发新版本。老的 `2023-06-01` 照样能用，不升也不会坏。

官方迁移说明：[migration-2026-10-21](https://platform.claude.com/docs/en/api/migration-2026-10-21)。

## 权限

Claude Code 默认每次工具调用都要手动批准。无人值守场景下这会卡住。cc-connect 在 `[projects.agent.options].mode` 里统一控制，`bypassPermissions` 全放行、`default` 要 IM 里回"允许"、`auto` 由 Claude 判断、`dontAsk` 没预授权的一律拒绝，见 [cc-connect 配置指南](docs/cc-connect-setup.md#权限模式)。

## FlClash 网络配置示例

[examples/flclash](examples/flclash/) 提供 Mac 和 Android 的固定出口分流模板，区分 Identity、日常主力和手动备用。公开文件不含节点、订阅或凭据，需要先在本地填写自己的出口，再导入使用。

## 常见问题

见 [troubleshooting](docs/troubleshooting.md)。

## 项目引用

- [Claude Code](https://github.com/anthropics/claude-code) — Anthropic 官方 CLI
- [cc-connect](https://github.com/chenhg5/cc-connect) — agent × IM 桥接器
- [Aelios](https://github.com/wusaki0723/Aelios) — 跑在 Cloudflare 上的长期记忆网关
- [Memos](https://github.com/usememos/memos) — 笔记/记忆系统（旧方案）

## License

MIT

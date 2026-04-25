# Claude Code Daily

让 Claude Code 24 小时在线，通过 IM 随时对话，具备跨 session 长期记忆。

适用场景：日常助手、知识管理、项目协作、消息代理，或任何需要 agent 持续在线的场景。

## 架构

```
┌──────────────────────────────────────────────┐
│              Agent CLI                        │
│   Claude Code / Codex / Gemini / Kimi ...     │
├──────────────────────────────────────────────┤
│  CLAUDE.md（行为规则 / 工具配置 / 上下文）    │
│  Memory（auto memory 或 Memos）               │
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
| Claude Code CLI（或其他 agent CLI）| 跑模型 | 是 |
| Claude 订阅 或 API key | 二选一 | 是 |
| CLAUDE.md | 行为规则和上下文 | 是 |
| cc-connect | IM ↔ agent 桥接 | 是 |
| Memos | 跨 session 长期记忆（tag + 全文） | 推荐 |
| memo-mcp | 无服务器向量记忆库（语义检索） | 可选 |
| systemd + tmux | 后台常驻 + 自动重启 | 推荐 |

cc-connect 支持的 agent（`[projects.agent.type]`）：`claudecode`、`codex`、`cursor`、`gemini`、`qoder`、`opencode`、`kimi`、`iflow`、任何 ACP 协议兼容的 agent。

支持的 IM 平台（`[[projects.platforms]]`）：Telegram、微信个人号（ilink）、企业微信、Discord、Slack、飞书/Lark、钉钉、LINE、微博、QQ（NapCat/OneBot）、QQ 官方 bot。

## 快速开始

### 1. 安装 Claude Code

```bash
# Node.js v18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo bash -
sudo apt-get install -y nodejs

npm install -g @anthropic-ai/claude-code
claude auth login
```

### 2. 工作区 + CLAUDE.md

```bash
mkdir -p ~/claude-workspace
cd ~/claude-workspace
```

在 `~/claude-workspace/CLAUDE.md` 里定义 Claude 的行为规则、输出风格、可用工具。参考 [examples/CLAUDE.md.example](examples/CLAUDE.md.example)。

### 3. 接入 IM

见 [cc-connect 配置指南](docs/cc-connect-setup.md)。

### 4. 长期记忆（可选）

见 [Memos 配置指南](docs/memos-setup.md)。如果想要"按意思找回"的语义检索，看下面 memo-mcp 一节。

### 5. 后台常驻

见 [后台运行指南](docs/background-running.md)。

## memo-mcp 无服务器向量记忆库

memo-mcp 是一个跑在 Cloudflare Worker 上的 MCP server，用 Vectorize 做向量存储、Workers AI 做 embedding。和 Memos 互补：Memos 走 tag 和全文搜索，memo-mcp 走语义检索。

适用场景：跨设备共享记忆、按"意思"检索而不是按关键词、不想自己维护服务器。

### 和 Memos 的区别

| 特性 | Memos | memo-mcp |
|------|-------|----------|
| 部署 | 自托管（Docker/二进制） | Cloudflare Worker（无服务器） |
| 检索 | 全文 + tag | 向量语义 |
| 状态 | SQLite 文件 | Vectorize 索引 + DO SQLite |
| 跨设备 | 需要公网/Tailscale | 自带 HTTPS endpoint |
| 成本 | 服务器电费 | 免费额度内 0 元 |
| 协议 | REST API | MCP（streamable HTTP / SSE） |

两者可并存。零碎日志和 tag 分类走 Memos，需要"按意思找回"的内容走 memo-mcp。

### 你会得到什么

- 一个 `https://memo-mcp.<你的子域>.workers.dev/mcp` 的 MCP 端点
- 四个工具：`write_memory`、`search_memory`、`get_memory`、`delete_memory`
- 全程在 Cloudflare 网页 dashboard 操作，不用装 wrangler、不用本地 Node

### 准备

只要一个 Cloudflare 账号（免费）和一个 GitHub 账号。

### 1. Fork 仓库

打开 [github.com/sakisakisa-design/claude-code-daily](https://github.com/sakisakisa-design/claude-code-daily) 点 **Fork**，fork 到你自己名下。

### 2. 在 Cloudflare 接 GitHub 部署 Worker

dashboard：**Workers & Pages → Create → Workers → Import a repository**

第一次会让你授权 Cloudflare 访问 GitHub，照做。

授权后选刚才 fork 的 `claude-code-daily` 仓库，配置三栏：

- **Project name**: `memo-mcp`（这就是后面 URL 的子域名前缀）
- **Production branch**: `main`
- **Build command**:
  ```
  cd examples/memo-mcp && npm install
  ```
- **Deploy command**:
  ```
  cd examples/memo-mcp && (npx wrangler vectorize create memo-kb --dimensions=768 --metric=cosine || true) && (npx wrangler vectorize create-metadata-index memo-kb --property-name=tags --type=string || true) && npx wrangler deploy
  ```
- **Advanced setting**: 不用动

点 **Save and deploy**。Cloudflare 会自己 cd 进 `examples/memo-mcp` 目录跑这两条命令：先建 Vectorize 索引（已存在就跳过，所以可以反复部署），再部署 Worker。几十秒搞定。

之后每次 push 到 fork 的 main 分支，自动重新部署。

### 3. 拿 endpoint 验证

部署完成后 dashboard 顶部会显示：

```
https://memo-mcp.<your-subdomain>.workers.dev
```

浏览器打开这个 URL，应该看到：

```
memo-mcp ok
endpoints: /mcp (streamable http), /sse (legacy)
```

Workers AI 绑定（embedding 用）和 Vectorize 绑定 Cloudflare 会按 `wrangler.toml` 自动注入，不用手动配。

### 4. 接入 Claude Code

```bash
claude mcp add --transport http memo-kb https://memo-mcp.<your-subdomain>.workers.dev/mcp
```

或者直接写到 `~/.claude/settings.json`：

```json
{
  "mcpServers": {
    "memo-kb": {
      "type": "http",
      "url": "https://memo-mcp.<your-subdomain>.workers.dev/mcp"
    }
  }
}
```

重启 Claude Code，`/mcp` 应该能看到 `memo-kb` 三个工具。

### 5. 使用

让 Claude 自己用，对话里说"记一下…"或"搜一下我之前说过…"，它会自动调对应工具。

手动调示例：

```
write_memory(content="用 wrangler tail 看 worker 实时日志", tags=["cf","ops"])
# → id=xxx-uuid

search_memory(query="怎么看 worker 日志", topK=3)
# → 每行一个 JSON：{"id":"...","score":0.83,"content":"...","tags":[...]}

search_memory(query="部署相关", tag="cf")

get_memory(ids=["xxx-uuid","yyy-uuid"])

# 更新已有记忆：拿 id 重新 write_memory（自动 upsert 覆盖）
write_memory(id="xxx-uuid", content="新内容", tags=["cf","ops"])

delete_memory(ids=["xxx-uuid"])
```

### 6. 在 CLAUDE.md 里引导用法（可选）

```markdown
## 长期记忆

走 memo-kb（MCP 向量库）：
- 重要事实、决策、配置 → write_memory，加 tags
- 想不起来某事是怎么解决的 → search_memory
- 失效信息 → delete_memory

只有需要"按意思找回"的内容才存这里。零碎日志和 tag 分类走 Memos。
```

### 安全和访问控制

`workers.dev` 子域名能被扫到（CF 索引 + 第三方爬虫），URL 一旦泄露就能任意读写删你的记忆。**强烈建议加一道 header 鉴权**。

代码已经内置：只要在 worker 上设了 `API_KEY` secret，所有 `/mcp` 和 `/sse` 请求都必须带 `x-api-key`（或 `Authorization: Bearer <key>`）才能通过；没设就放行（兼容首次部署）。

**严格按这个顺序操作**，否则中间会有客户端连不上的窗口期。

#### 1. 生成密钥

Mac / Linux 终端：

```bash
openssl rand -hex 32
```

Windows / 没装 openssl：用 [random.org](https://www.random.org/strings/?num=1&len=32&digits=on&loweralpha=on&unique=on&format=html&rnd=new) 生一串 32 位，或者直接复制下面这串自己改几个字符（**别原样用**）：

```
b32a8672b641ecc352c0d9b968addd4171c324fde61b151dde5886098a387a7a
```

把它存好，下面三步都要用。

#### 2. 先把客户端 header 准备好

**Claude Code**（编辑 `~/.claude/settings.json`，没有就新建）：

```json
{
  "mcpServers": {
    "memo-kb": {
      "type": "http",
      "url": "https://memo-mcp.<your-subdomain>.workers.dev/mcp",
      "headers": { "x-api-key": "刚才那串密钥" }
    }
  }
}
```

**Claude.ai 网页**：Settings → Connectors → 找到 `memo-kb` → 编辑 → 展开 **Advanced** / **Custom headers** → 加一行：

| Name | Value |
|------|-------|
| `x-api-key` | 刚才那串密钥 |

保存。

> 现在客户端会带 header，但 worker 还没要求验证，所以照常工作。

#### 3. 在 CF dashboard 设 secret

Worker 详情 → **Settings → Variables and Secrets → Add → Type: Secret**

- Name: `API_KEY`（注意大小写，必须就是这个名字）
- Value: 你的密钥

点 Save。CF 会自动在几秒内重新部署 worker，从这一刻起没带 header 的请求一律 401。

#### 4. 验证

终端跑这条（替换 URL）：

```bash
# 不带 header，应该 401
curl -i https://memo-mcp.<your-subdomain>.workers.dev/mcp

# 带 header，应该走到 MCP（不会是 401，可能是 400 或 405，因为不是合法的 MCP 请求体，但说明鉴权过了）
curl -i -H "x-api-key: 你的密钥" https://memo-mcp.<your-subdomain>.workers.dev/mcp
```

然后回 Claude Code / Claude.ai 试一下 `search_memory` 能不能用。

**忘了密钥 / 想换密钥**：dashboard 把 secret 删掉重设，再回客户端把 header 同步成新值。

**更严的方案**

想要 SSO / 邮箱白名单可以叠 Cloudflare Access：在 zero-trust dashboard 给这个 Worker 配 Access policy。但 Access 不太适合无人值守的 MCP 调用，所以一般 header 鉴权够用。

### 常见问题

**部署日志里报 `vectorize index not found` 或 `binding ... not bound`**
索引还没建，或者名字不是 `memo-kb`。回到 dashboard 的 AI → Vectorize 里检查，名字必须和 `wrangler.toml` 里的 `index_name` 完全一致。

**Claude 看不到 memo-kb 工具**
- 确认 Claude Code 版本支持 streamable HTTP transport
- 看 `~/.claude/logs/` 里 MCP 连接报错
- 旧版本退回 SSE：URL 改成 `.../sse`

**搜出来的结果不相关**
- 写的时候 content 太短，embedding 信息量不够。每条至少一句完整的话
- 检索时 query 写完整问题，别只给关键词
- 同语种检索更准

**怎么批量导入已有内容**
临时本地装一次 wrangler（`npm i -g wrangler && wrangler login`），用 `wrangler vectorize insert` 直接灌数据，绕过 Worker。或者写个脚本循环 HTTP 调 `/mcp` 的 write_memory。

**改了代码 dashboard 没自动部署**
检查 fork 仓库的 push 是不是到了 main 分支；Cloudflare 在 Worker 详情 → **Builds** 里能看到每次构建日志。

### 成本预估

| 项目 | 免费额度 | 满负载场景 |
|------|----------|-----------|
| Workers 请求 | 10 万/天 | 一天 1000 次远没用完 |
| Workers AI | 10000 神经元/天 | embedding 一次 ~1 神经元 |
| Vectorize 存储 | 500 万维度 | 6500 条 × 768 维 |
| Vectorize 查询 | 3000 万维度/月 | 一天 1000 次完全够 |
| Durable Objects | 1G-s/天 | MCP session 状态，几乎不消耗 |

个人用基本 0 元。重度用一个月几块到十几块封顶。

### 进阶

改完代码 push 到 fork，Cloudflare 自动重新部署。可以折腾的方向：

- 加 `list_tags`：从 metadata 聚合所有 tag
- 换更强的 embedding：`@cf/baai/bge-m3`（1024 维）召回更好但贵一点。换之前要在 dashboard 重建一个对应维度的 Vectorize 索引
- 把检索结果作为 hook 注入 Claude 上下文，参考 [memos-setup.md](docs/memos-setup.md) 的 `query_kb.sh`

代码在 [examples/memo-mcp](examples/memo-mcp)。

## 权限

Claude Code 默认每次工具调用都要手动批准。无人值守场景下这会卡住。cc-connect 在 `[projects.agent.options].mode` 里统一控制，`bypassPermissions` 全放行、`default` 要 IM 里回"允许"、`auto` 由 Claude 判断，见 [cc-connect 配置指南](docs/cc-connect-setup.md#权限模式)。

## 常见问题

见 [troubleshooting](docs/troubleshooting.md)。

## 项目引用

- [Claude Code](https://github.com/anthropics/claude-code) — Anthropic 官方 CLI
- [cc-connect](https://github.com/chenhg5/cc-connect) — agent × IM 桥接器
- [Memos](https://github.com/usememos/memos) — 笔记/记忆系统

## License

MIT

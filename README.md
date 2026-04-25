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
- 三个工具：`write_memory`、`search_memory`、`delete_memory`
- 全程在 Cloudflare 网页 dashboard 操作，不用装 wrangler、不用本地 Node

### 准备

只要一个 Cloudflare 账号（免费）和一个 GitHub 账号。

### 1. Fork 仓库

打开 [github.com/sakisakisa-design/claude-code-daily](https://github.com/sakisakisa-design/claude-code-daily) 点 **Fork**，fork 到你自己名下。

代码在 `examples/memo-mcp/`，下一步会让 Cloudflare 直接从这个目录构建。

### 2. 在 Cloudflare 创建 Vectorize 索引

打开 dashboard：**AI → Vectorize → Create index**

- Name: `memo-kb`
- Dimensions: `768`
- Metric: `Cosine`

创建完，再点进这个索引 → **Metadata indexes → Create** 加一个：

- Property name: `tags`
- Type: `String`

（不加这个 metadata index，`search_memory` 的 `tag` 过滤会报错。）

### 3. 在 Cloudflare 接 GitHub 部署 Worker

dashboard：**Workers & Pages → Create → Workers → Import a repository**

第一次会让你授权 Cloudflare 访问 GitHub，照做。

授权后选刚才 fork 的 `claude-code-daily` 仓库，配置：

- **Project name**: `memo-mcp`（这个就是后面 URL 的子域名前缀）
- **Production branch**: `main`
- **Root directory**: `examples/memo-mcp`
- **Build command**: 留空（wrangler.toml 已经够用）
- **Deploy command**: `npx wrangler deploy`

点 **Create and deploy**。Cloudflare 会自动跑 `npm install` + `npx wrangler deploy`，几十秒内完成。

之后每次你 push 到 fork 的 main 分支，Cloudflare 会自动重新部署。

### 4. 拿 endpoint 验证

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

### 5. 接入 Claude Code

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

### 6. 使用

让 Claude 自己用，对话里说"记一下…"或"搜一下我之前说过…"，它会自动调对应工具。

手动调示例：

```
write_memory(content="用 wrangler tail 看 worker 实时日志", tags=["cf","ops"])
search_memory(query="怎么看 worker 日志", topK=3)
search_memory(query="部署相关", tag="cf")
```

### 6. 在 CLAUDE.md 里引导用法

```markdown
## 长期记忆

走 memo-kb（MCP 向量库）：
- 重要事实、决策、配置 → write_memory，加 tags
- 想不起来某事是怎么解决的 → search_memory
- 失效信息 → delete_memory

只有需要"按意思找回"的内容才存这里。零碎日志和 tag 分类走 Memos。
```

### 安全和访问控制

默认 Worker 没鉴权，谁拿到 URL 都能读写。生产环境建议加一道：

**方式 1：Cloudflare Access**

在 zero-trust dashboard 给这个 Worker 配 Access policy，要求邮箱白名单或 service token。

**方式 2：自定义 header 校验**

在 fork 的 `src/index.ts` 的 `fetch` 入口加：

```typescript
const auth = request.headers.get("x-api-key");
if (auth !== env.API_KEY) {
  return new Response("unauthorized", { status: 401 });
}
```

提交 push，Cloudflare 会自动重新部署。然后到 dashboard：**Worker 详情 → Settings → Variables and Secrets → Add → Type: Secret**，name 填 `API_KEY`，value 填一个长随机串。

Claude Code 这边 `mcpServers` 里加 `headers`：

```json
{
  "memo-kb": {
    "type": "http",
    "url": "https://...",
    "headers": { "x-api-key": "your-secret" }
  }
}
```

### 常见问题

**部署日志里报 `vectorize index not found` 或 `binding ... not bound`**
索引还没建，或者名字不是 `memo-kb`。回到 dashboard 的 AI → Vectorize 里检查，名字必须和 `wrangler.toml` 里的 `index_name` 完全一致。

**部署日志里报 metadata index 相关错误**
没建 `tags` 那个 metadata index。回到 Vectorize 索引详情页加上。

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

- 加 `update_memory`：先 query 出 id，再 upsert 同 id 覆盖
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

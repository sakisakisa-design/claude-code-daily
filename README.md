# Claude Code Daily

让 Claude Code / Codex 24 小时在线，通过 IM 随时对话，具备跨 session 长期记忆。

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
| Claude Code CLI 或 Codex CLI | 跑模型 | 是 |
| Claude 订阅 / ChatGPT 订阅 / API key | 三选一 | 是 |
| CLAUDE.md / AGENTS.md | 行为规则和上下文 | 是 |
| cc-connect | IM ↔ agent 桥接 | 是 |
| Memos | 跨 session 长期记忆（tag + 全文） | 推荐 |
| memo-mcp | 无服务器向量记忆库（语义检索） | 可选 |
| systemd + tmux | 后台常驻 + 自动重启 | 推荐 |

cc-connect 支持的 agent（`[projects.agent.type]`）：`claudecode`、`codex`、`cursor`、`gemini`、`qoder`、`opencode`、`kimi`、`iflow`、任何 ACP 协议兼容的 agent。

支持的 IM 平台（`[[projects.platforms]]`）：Telegram、微信个人号（ilink）、企业微信、Discord、Slack、飞书/Lark、钉钉、LINE、微博、QQ（NapCat/OneBot）、QQ 官方 bot。

## 给 AI / Agent 的阅读入口

如果你把这个仓库丢给 Claude Code、Codex、Cursor、Gemini CLI 或其他 agent，让它按仓库帮你部署，优先读这些文件：

1. `README.md`：整体架构、memo-mcp Cloudflare Worker 部署
2. `docs/cc-connect-setup.md`：IM 桥接配置
3. `docs/codex-setup.md`：Codex CLI 接入 cc-connect
4. `docs/memos-setup.md`：Memos 长期记忆
5. `docs/background-running.md`：systemd / launchd 常驻
6. `docs/troubleshooting.md`：常见故障

目标是跑通一条链路：`IM → cc-connect → Agent CLI → 工作区规则文件 → 长期记忆`。

## 快速开始

### 1. 安装 Agent CLI

Claude Code 路线：

```bash
# Node.js v18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo bash -
sudo apt-get install -y nodejs

npm install -g @anthropic-ai/claude-code
claude auth login
```

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

### 4. 长期记忆（可选）

见 [Memos 配置指南](docs/memos-setup.md)。如果想要"按意思找回"的语义检索，看下面 memo-mcp 一节。

### 5. 后台常驻

见 [后台运行指南](docs/background-running.md)。

## Claude API 接入

订阅（Pro / Max）走 `claude auth login` 就够了，下面是没订阅、想按量付费的几条路。

### 在 Cloudflare AI Gateway 买 Claude API

适合 Anthropic 直充不通、或想顺便拿 Gateway 的统计、缓存、限流能力的人。最低 10 美元起充，5% 手续费，价格官方价不加。拿到的 endpoint 和 `cfut_` token 可以喂给 Claude Code、Claude Desktop 或自己的脚本。

完整教程：[docs/cf-claude-api.md](docs/cf-claude-api.md)，含 prompt cache 命中坑（必须加 `cf-aig-skip-cache: true` 且 system 转数组带 `cache_control`）。

### Claude Desktop 接入第三方 API

Claude Desktop 自带 **Cowork on 3P** 模式，可以不登 Anthropic 账号、直接用 CF AI Gateway / Vertex / Bedrock / Foundry 跑。GUI 用户、被 ban 账号、或者公司统一用 Vertex 的场景适用。

完整教程：[docs/claude-desktop-3p.md](docs/claude-desktop-3p.md)，含个人路径（Apply locally）和企业 MDM 路径的入口区别。

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

如果你让 AI 或命令行替你部署，也可以直接 `git clone` 或下载 ZIP，再用 `wrangler deploy` 部署；只有走 Cloudflare Dashboard 的 GitHub 自动部署时，fork 最省事。

### 2. 在 Cloudflare 接 GitHub 部署 Worker

dashboard：**Workers & Pages → Create → Workers → Import a repository**

第一次会让你授权 Cloudflare 访问 GitHub，照做。

授权后选刚才 fork 的 `claude-code-daily` 仓库，配置三栏：

- **Project name**: 项目名 = URL 子域名前缀，**强烈建议用随机串**（例如 `kb-` 加几个随机字符，或者 `openssl rand -hex 4` 生一段），不要用 `memo-mcp` 这种好猜的。这是你的第一道安全线 — workers.dev 的子域名会被爬虫扫，名字越独特越难命中。
- **Production branch**: `main`
- **Build command**:
  ```
  cd examples/memo-mcp && npm install
  ```
- **Deploy command**（注意 `--name` 后面填和你上面项目名一样的值）：
  ```
  cd examples/memo-mcp && (npx wrangler vectorize create memo-kb --dimensions=768 --metric=cosine || true) && (npx wrangler vectorize create-metadata-index memo-kb --property-name=tags --type=string || true) && npx wrangler deploy --name 你的项目名
  ```
- **Advanced setting**: 不用动

点 **Save and deploy**。Cloudflare 会自己 cd 进 `examples/memo-mcp` 目录跑这两条命令：先建 Vectorize 索引（已存在就跳过，所以可以反复部署），再部署 Worker。几十秒搞定。

之后每次 push 到 fork 的 main 分支，自动重新部署。

### 3. 拿 endpoint 验证

部署完成后 dashboard 顶部会显示：

```
https://<你的项目名>.<your-subdomain>.workers.dev
```

浏览器打开这个 URL，应该看到：

```
memo-mcp ok
endpoints: /mcp (streamable http), /sse (legacy)
```

Workers AI 绑定（embedding 用）和 Vectorize 绑定 Cloudflare 会按 `wrangler.toml` 自动注入，不用手动配。

### 4. 接入 Claude Code / Codex

Claude Code：

```bash
claude mcp add --transport http memo-kb https://<你的项目名>.<your-subdomain>.workers.dev/mcp
```

或者直接写到 `~/.claude/settings.json`：

```json
{
  "mcpServers": {
    "memo-kb": {
      "type": "http",
      "url": "https://<你的项目名>.<your-subdomain>.workers.dev/mcp"
    }
  }
}
```

重启 Claude Code，`/mcp` 应该能看到 `memo-kb` 四个工具。

Codex：

```bash
codex mcp add memo-kb --url https://<你的项目名>.<your-subdomain>.workers.dev/mcp
```

或者写到 `~/.codex/config.toml`：

```toml
[mcp_servers.memo-kb]
url = "https://<你的项目名>.<your-subdomain>.workers.dev/mcp"
```

如果你用了 `API_KEY` secret，Codex 可以直接把 token 放 URL 里：

```bash
codex mcp add memo-kb --url 'https://<你的项目名>.<your-subdomain>.workers.dev/mcp?token=你的token'
```

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

`workers.dev` 子域名会被爬虫扫，URL 一旦泄露就能任意读写删你的记忆。三种思路按强度从弱到强：

#### 方案 A：URL 当密码（最低限度）

部署时项目名用足够随机的串（上面步骤 2 已经强调），URL 形如 `kb-7g3h.<subdomain>.workers.dev`，靠枚举命中概率很低。无需配置任何 secret。

注意：
- 部署后**别在公开地方贴你的 URL**（聊天记录、截图、博客）
- fork 仓库可以保持公开，因为项目名不在代码里（在 CF dashboard 里）
- 想换 URL 就在 CF dashboard 重新建一个 worker，新名字，旧的删掉

#### 方案 B：URL 加 ?token= 查询串（推荐，兼容所有客户端）

跟方案 A 一样不用配 OAuth，但多一道密钥。Claude.ai connector / Claude Code / 任何只接受单个 URL 的 MCP 客户端都能用。

**步骤**：

1. 生成 token：`openssl rand -hex 32`（Windows 用 [random.org](https://www.random.org/strings/?num=1&len=32&digits=on&loweralpha=on)）
2. CF dashboard → Worker 详情 → **Settings → Variables and Secrets → Add → Type: Secret**：Name `API_KEY`，Value 你的 token
3. 客户端用带 token 的完整 URL：
   ```
   https://<你的项目名>.<your-subdomain>.workers.dev/mcp?token=你的token
   ```
   - **Claude.ai connector**：URL 那栏直接填上面这串（含 `?token=`）
   - **Claude Code** `~/.claude/settings.json`：
     ```json
     {
       "mcpServers": {
         "memo-kb": {
           "type": "http",
           "url": "https://<...>/mcp?token=你的token"
         }
       }
     }
     ```

**注意**：URL 里有 token 意味着 token 可能进 CF 的访问日志，所以这个 token 不算最高安全级别。但比裸 URL 强很多，且兼容性最好。

#### 方案 C：HTTP header 鉴权（最强，但 Claude.ai 不兼容）

Claude.ai 自定义 connector 走 OAuth 2.0，不会传 header；只在 Claude Code / 自己脚本里用 MCP 时可以叠这一道。

设了 `API_KEY` secret 后，请求带下面任一 header 都通过：
- `x-api-key: <key>`
- `Authorization: Bearer <key>`
- `Authorization: Basic <base64(任何用户名:key 或 key:任何密码)>`

Claude Code `~/.claude/settings.json`：

```json
{
  "mcpServers": {
    "memo-kb": {
      "type": "http",
      "url": "https://<你的项目名>.<your-subdomain>.workers.dev/mcp",
      "headers": { "x-api-key": "你的密钥" }
    }
  }
}
```

> 验证：`curl -i https://<...>/mcp` 应 401；`curl -i -H "x-api-key: 你的密钥" https://<...>/mcp` 应不是 401。

#### 注意：方案 B 和 C 共用同一个 `API_KEY` secret

设一次 secret，三种方式（query/header/basic）任意一个对的就放行。所以可以同时给手机用 query、给本地脚本用 header。

#### 更严

要 SSO / 邮箱白名单可以叠 Cloudflare Access。但 Access 需要交互式登录，跟无人值守的 MCP 不太搭。

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

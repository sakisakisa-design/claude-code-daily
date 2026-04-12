# Memos 记忆系统配置

Claude Code 自带的 auto memory 是基于文件的，重启 session 后通过 MEMORY.md 索引加载。但 Memos 提供了更灵活的长期记忆方案：tag 分类、全文搜索、API 读写，适合需要结构化记忆的场景。

## 安装 Memos

### 方式 1：Docker（推荐）

```bash
# 创建数据目录
mkdir -p ~/memos-data

# 启动容器
docker run -d \
  --name memos \
  --restart always \
  -p 5230:5230 \
  -v ~/memos-data:/var/opt/memos \
  neosmemo/memos:stable
```

验证：

```bash
curl http://localhost:5230/api/v1/ping
```

如果没有安装 Docker：

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y docker.io
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
# 重新登录 shell 使 docker 组生效
```

### 方式 2：直接安装

参考 [Memos 官方文档](https://www.usememos.com/docs/install/self-hosting)。

## 初始配置

1. 打开 `http://你的服务器IP:5230`
2. 创建管理员账号
3. 在 Settings → API → Access Tokens 创建一个 Token
4. 保存 Token（格式：`memos_pat_xxxxx`）

## 在 CLAUDE.md 中集成

在你的 `CLAUDE.md` 中添加以下内容，让 Claude 知道如何使用 Memos：

```markdown
## 记忆系统

所有长期记忆存 Memos，用 tag 分类：#daily #feedback #personal #project #rules

### 会话启动时加载

每次新 session 启动时，读取今天和昨天的日志以及规则：

\```
curl -s "http://localhost:5230/api/v1/memos?filter=%22$(date +%Y-%m-%d)%22+in+tags" \
  -H "Authorization: Bearer YOUR_TOKEN" -H "Accept: application/json"
curl -s "http://localhost:5230/api/v1/memos?filter=%22$(date -d yesterday +%Y-%m-%d)%22+in+tags" \
  -H "Authorization: Bearer YOUR_TOKEN" -H "Accept: application/json"
curl -s "http://localhost:5230/api/v1/memos?filter=%22rules%22+in+tags" \
  -H "Authorization: Bearer YOUR_TOKEN" -H "Accept: application/json"
\```

### 读取
\```bash
curl -s "http://localhost:5230/api/v1/memos?pageSize=10" \
  -H "Authorization: Bearer YOUR_TOKEN" -H "Accept: application/json"
\```

### 创建
\```bash
curl -s -X POST http://localhost:5230/api/v1/memos \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"content":"内容","visibility":"PRIVATE"}'
\```

### 按 tag 搜索
\```bash
curl -s "http://localhost:5230/api/v1/memos?filter=%22tagname%22+in+tags" \
  -H "Authorization: Bearer YOUR_TOKEN" -H "Accept: application/json"
\```

### 按内容搜索
\```bash
curl -s "http://localhost:5230/api/v1/memos?filter=content_search%3D%3D%22关键词%22" \
  -H "Authorization: Bearer YOUR_TOKEN" -H "Accept: application/json"
\```
```

## Tag 设计建议

| Tag | 用途 |
|-----|------|
| `#daily` `#YYYY-MM-DD` | 每日会话日志 |
| `#rules` | 持久性规则（如违规计数） |
| `#feedback` | 用户反馈和偏好 |
| `#personal` | 用户个人信息 |
| `#project` | 项目/技术笔记 |

## 日志格式建议

```
#daily #2026-04-12 Claude code
- 今天聊了什么
- 做了什么事
- 关键决策或变化
```

## Memos vs Auto Memory

| 特性 | Auto Memory | Memos |
|------|-------------|-------|
| 存储位置 | 本地文件 (~/.claude/memory/) | 独立服务 (SQLite) |
| 跨 session | 通过 MEMORY.md 索引 | 通过 API 查询 |
| 搜索 | 文件名匹配 | 全文搜索 + tag 过滤 |
| 结构化 | frontmatter | tag 系统 |
| 备份 | git | 数据库文件 |
| Web UI | 无 | 有 |

两者可以同时使用，不冲突。Auto Memory 适合存 Claude 自动学到的东西，Memos 适合存你主动要求记录的内容。

## Hook：自动检索知识库

可以配置一个 `UserPromptSubmit` hook，让 Claude 每次收到消息时自动从 Memos 检索相关内容，作为上下文注入。

### 1. 创建检索脚本

创建 `~/claude-workspace/scripts/query_kb.sh`：

```bash
#!/bin/bash
# 知识库检索入口
# Hook 模式: 从 stdin 读取 JSON，提取 prompt 字段
# 手动模式: query_kb.sh "关键词"

TOP_K="${2:-3}"

if [ -n "$1" ]; then
    QUERY="$1"
else
    INPUT=$(cat)
    QUERY=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('prompt',''))" 2>/dev/null)
fi

if [ -z "$QUERY" ]; then
    echo "[知识库检索结果] 无查询内容"
    exit 0
fi

# 简单实现：直接用 Memos 的内容搜索
ENCODED=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$QUERY'))")
RESULT=$(curl -s "http://localhost:5230/api/v1/memos?filter=content_search%3D%3D%22${ENCODED}%22&pageSize=${TOP_K}" \
  -H "Authorization: Bearer YOUR_MEMOS_TOKEN" \
  -H "Accept: application/json" 2>/dev/null)

# 提取内容摘要
CONTENT=$(echo "$RESULT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    memos = data.get('memos', [])
    if not memos:
        print('[知识库检索结果] 未找到相关内容')
    else:
        for m in memos:
            snippet = m.get('snippet', m.get('content', '')[:100])
            print(f'- {snippet}')
except:
    print('[知识库检索结果] 检索失败')
" 2>/dev/null)

echo "$CONTENT"
```

```bash
chmod +x ~/claude-workspace/scripts/query_kb.sh
```

> 上面是最简实现，直接用 Memos API 的文本搜索。如果需要更精准的语义检索，可以加一层 embedding 向量数据库（如 chromadb）做 RAG。

### 2. 在 settings.json 中注册 hook

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash ~/claude-workspace/scripts/query_kb.sh",
            "timeout": 30,
            "statusMessage": "检索知识库..."
          }
        ]
      }
    ]
  }
}
```

这样每次收到消息，Claude 会先检索 Memos 中的相关记忆，检索结果会作为上下文附加在消息中。

## 注意事项

- Memos 的 filter 使用 CEL 语法，搜 tag 用 `"tagname" in tags`，不要用 `content_search` 搜 tag
- 如果用 Mac mini，Docker 装法一样，只是注意 macOS 的 Docker Desktop 性能开销
- Memos 数据存在 `~/memos-data/memos_prod.db`，定期备份这个文件即可

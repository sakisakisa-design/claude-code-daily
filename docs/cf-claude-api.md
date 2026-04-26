# 在 Cloudflare AI Gateway 买 Claude API

适用场景：

- Anthropic 直充不方便（地区/支付方式），想用人民币/美元国际卡走 Cloudflare 计费
- 想顺便拿 CF Gateway 的统计、缓存、限流、回退能力
- 想给 Claude Desktop / Claude Code / 自己脚本一个统一的 endpoint

不适用场景：

- 已经有 Anthropic 直充的 API key，没必要再绕一层（CF 收 5% 手续费）
- 想白嫖（Gateway 不送额度，充 10 刀实付 10.5 刀）

## 步骤

### 1. 开通 AI Gateway

CF dashboard：**AI → AI Gateway → Create new gateway**

随便起个名字（gateway 名字不影响安全，仅作分组），创建后会拿到一个 URL：

```
https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_name}/
```

记下来，下面所有调用都基于这个前缀。

### 2. 充值 credits

**AI Gateway → Billing → Buy credits**

最低 10 美元起充，5% 手续费（想充 10 刀实付 10.5 刀，到账 10 刀）。按 token 实时扣，不限时间不订阅。

### 3. 创建 token

**AI Gateway → Settings → Create token**

token 形如 `cfut_xxxxxxxxxx`，作为客户端鉴权用。两种用法等价：

- `cf-aig-authorization: Bearer cfut_xxx`
- `x-api-key: cfut_xxx`

可以建多个 token 给不同设备/用途，单独吊销。

### 4. 选端点

CF 给 Anthropic 准备了两个端点：

| 端点 | 格式 | prompt cache |
|------|------|--------------|
| `/anthropic/v1/messages` | Anthropic 原生 | 支持，**推荐** |
| `/compat/chat/completions` | OpenAI 兼容 | 不支持（传不了 `cache_control`） |

只要客户端能传 Anthropic 格式，就走 `/anthropic/v1/messages`，否则就走 `/compat`。

### 5. 调用测试

最干净的 curl 示例：

```bash
curl https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_name}/anthropic/v1/messages \
  -H "anthropic-version: 2023-06-01" \
  -H "cf-aig-authorization: Bearer cfut_xxx" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-haiku-4-5",
    "max_tokens": 64,
    "messages": [{"role":"user","content":"ping"}]
  }'
```

返回正常的 `content` 数组就通了。Gateway 上能在 **Logs** 里看到这次调用。

### 6. 接 Claude Code

`~/.claude/settings.json` 或环境变量都行。环境变量更省事：

```bash
export ANTHROPIC_BASE_URL="https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_name}/anthropic"
export ANTHROPIC_API_KEY="cfut_xxx"
```

之后 `claude` 命令照常用，所有请求走 CF Gateway。

### 7. 接 Claude Desktop

Claude Desktop 走 third-party inference 模式，配置方式见 [claude-desktop-3p.md](claude-desktop-3p.md)。Provider 选 **Gateway**，URL 和 token 用上面拿到的。

## 命中 Prompt Cache

CF Gateway 默认会做一道**语义缓存**（同语义的 query 直接返结果），这会拦截请求让 Anthropic 自家的 prompt cache 用不上。

典型表现：连续打同一个长 system 请求，每次 `usage` 里 `cache_creation_input_tokens` 非零、`cache_read_input_tokens` 永远是 0，看起来 cache 从来不命中。

两件事一起做才能命中。

### 1. 关掉 CF 语义缓存

每次请求加 header：

```
cf-aig-skip-cache: true
```

或者干脆在 Gateway 面板把整个 Cache 关掉（**Settings → Cache**）。

### 2. 显式声明 prompt cache 块

把 `system` 字段从字符串转成数组，加 `cache_control`：

```json
{
  "model": "claude-haiku-4-5",
  "system": [
    {
      "type": "text",
      "text": "你的长系统提示...",
      "cache_control": {"type": "ephemeral", "ttl": "5m"}
    }
  ],
  "messages": []
}
```

`ttl` 可选 `5m` 或 `1h`，5 分钟够 90% 场景，长会话用 1h。

### 3. 等 1 秒传播

cache 建立后**约 1 秒传播延迟**，第一次请求建好 cache 之后，立刻打第二个相同请求会全 miss 走 cache_creation。

第一次建立后等 1 秒再打后续请求，之后稳定命中。脚本里测 cache 命中率必须考虑这个间隔。

### 4. Haiku 的额外限制

Haiku 要求至少 **2048 tokens** 的 prefix 才会进入 cache。短 system 不会被 cache，省下来的钱只够买根冰棍。

### 验证

响应的 `usage` 里：

- 第一次：`cache_creation_input_tokens` 有数，`cache_read_input_tokens` 是 0
- 第二次起（间隔 ≥1 秒）：`cache_creation_input_tokens` 是 0，`cache_read_input_tokens` 有数

两者都不为 0 就对了。

### 价格参考（Opus 4.6）

| 项 | 单价 |
|----|------|
| input | $5/M |
| cache_creation | $6.25/M |
| cache_read | $0.5/M |
| output | $25/M |

cache 命中后 input 部分变成原价的 10%。长 system + 多轮对话场景，cache 是省钱大头。

## 反代 Worker（可选）

适用场景：

- 客户端只接受标准 Anthropic API（base URL + key），传不了 `cf-aig-authorization` / `cf-aig-skip-cache` 这种自定义 header
- 用了 CPA、new-api 这类多渠道网关，它们也传不了 CF 特殊 header
- 想给所有客户端统一暴露成 "Anthropic 原生 API" 的样子，CF 鉴权细节藏在反代里

最快的做法：把下面这段 prompt 丢给 Claude / Codex / GPT，它会写出 Worker 代码：

```
用 Cloudflare Workers 写一个反代脚本：前端暴露 Anthropic 原生 API
（POST /v1/messages 和 GET /v1/models），后端转发到
https://gateway.ai.cloudflare.com/v1/{ACCOUNT}/{GATEWAY}/anthropic 。
要求：
1) 把客户端进来的 x-api-key 删掉，统一加上
   cf-aig-authorization: Bearer {CFUT_TOKEN} 和 cf-aig-skip-cache: true 两个 header；
2) /v1/messages 透传 body 和 SSE stream；
3) /v1/models 直接返回写死的 Claude 模型列表（Anthropic 没这个端点）；
4) 如果 system 字段是字符串且长度大于 200，自动转成
   [{type:"text",text:...,cache_control:{type:"ephemeral",ttl:"5m"}}]
   数组格式以确保命中 prompt cache。
```

部署完之后，客户端把 `ANTHROPIC_BASE_URL` 指向你的 Worker URL，`ANTHROPIC_API_KEY` 随便填一个（或者你在 Worker 里加自己的鉴权层）。

## 常见坑

**Logs 里看到 401**
token 拼错了，或者 `cf-aig-authorization` 写成了 `cf-aig-authentication`。

**返回 524 / 408**
Gateway 默认超时 100 秒，长上下文 + 长输出可能超。dashboard 里把 Gateway 的 **Request timeout** 拉大。

**第三方客户端不让传 CF header**
`cf-aig-authorization` 不接受时，把 token 放到 `x-api-key` 一样过。`cf-aig-skip-cache` 没法传时，去 dashboard 把整个 gateway 的 **Cache** 关掉。

**充值显示 pending**
CF credits 充值偶尔卡几分钟到半小时，不是异常，等就好。

**多渠道网关（CPA / new-api）接 CF 失败**
这类网关有几个共同坑：1) 配置基本不支持热加载，改完必须重启进程，"保存成功"是假象；2) 默认把 api-key 当 `x-api-key` 透给上游，CF token 会被 Anthropic 拒（`x-api-key header is required`），第一次失败渠道会进 cooldown；3) 部分网关对 api-key 字段强制非空校验，必须在 entry 里配自定义 header 才能加 `cf-aig-authorization`；4) 某些 provider 类型对 model name 强校验/normalize，简短名注册不上。最稳的做法：自建反代（上面那段）暴露成 OpenAI 兼容 endpoint，网关用 openai-compatibility provider 接入，model name 起个网关没见过的别名（比如 `cf-h45`），反代里映射回真实模型名。

## 成本对比

| 项目 | Anthropic 直充 | CF AI Gateway |
|------|---------------|---------------|
| 最低充值 | 5 美元 | 10 美元 |
| 手续费 | 0% | 5% |
| 国际卡支付 | 部分地区受限 | 全球通用 |
| 价格 | 官方价 | 官方价（不加价，只收一次性手续费） |
| 缓存/限流/统计 | 自己做 | Gateway 自带 |

只调 API 不在乎统计就直充划算，要 Gateway 工具链或者直充不通就走 CF。

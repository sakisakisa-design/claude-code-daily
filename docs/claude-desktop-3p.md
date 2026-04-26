# Claude Desktop 接入第三方 API

Claude Desktop 默认走 Anthropic 自家账号登录。它还有一个**第三方推理模式**（Cowork on 3P），可以让 Claude Desktop 不登录 Anthropic、直接用别的推理后端跑，比如：

- Cloudflare AI Gateway（用 CF credits 跑 Claude）
- Google Vertex AI
- AWS Bedrock
- Azure AI Foundry

适用场景：

- 没有 Anthropic 账号或被 ban，但想用 Claude Desktop 这个 GUI
- 想用自己买的 CF / Bedrock / Vertex 额度
- 公司统一走 Vertex / Bedrock，员工想用 Claude Desktop

不适用场景：

- 你只想用 Claude Code CLI，不需要 GUI（直接给 Claude Code 配 `ANTHROPIC_BASE_URL` 就行）

下面是个人用户路径，企业 MDM 部署见[官方文档](https://claude.com/docs/cowork/3p/installation#admin-installation)。

## 步骤

### 1. 装 Claude Desktop

[claude.com/download](https://claude.com/download)，选你的平台：

- macOS: `.dmg`，拖 Claude.app 到 Applications
- Windows: `.msix`

### 2. 启动，不要登录

打开 Claude Desktop，**停在登录屏幕，不要点 Sign in、不要点 Create account**。一旦登录到 Anthropic 账号，第三方推理模式的入口会被锁掉。

### 3. 开开发者模式

**macOS**：屏幕顶部菜单栏 → **Help → Troubleshooting → Enable Developer Mode**

**Windows**：登录屏幕左上角应用菜单（☰）→ **Help → Troubleshooting → Enable Developer Mode**

打开后菜单里会多一个 **Developer**。

### 4. 进配置窗口

**Developer → Configure third-party inference**

会弹出一个配置窗口，左边七个分区。第一个 **Connection** 是必填的，剩下的（Sandbox、Connectors、Telemetry、Usage limits、Plugins、Egress）都有合理默认值，先跳过。

### 5. 填 Connection

**Inference provider** 四选一：

| Provider | 后端 | 凭证类型 |
|----------|------|----------|
| Gateway | CF AI Gateway 或任何 Anthropic 兼容 endpoint | URL + API key |
| Vertex | Google Vertex AI | GCP service account |
| Bedrock | AWS Bedrock | AWS access key |
| Foundry | Azure AI Foundry | Azure key |

**用 CF AI Gateway 的填法**（参考 [cf-claude-api.md](cf-claude-api.md) 拿到 URL 和 token）：

- Provider: `Gateway`
- Endpoint URL: `https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_name}/anthropic`
- API key: `cfut_xxx`
- Model list: 至少填一个，比如 `claude-sonnet-4-5`、`claude-opus-4-7`、`claude-haiku-4-5`，多个用逗号分隔
- Organization UUID: 任意 UUID（v4 即可），用于本地标识，不上传

**Vertex / Bedrock / Foundry** 的具体字段照官方说明填，每个 provider 进了配置窗口会自动列出它需要的字段。

### 6. 测试

填完点 **Apply locally**（不是 Export，Export 是给 IT 管理员批量分发用的）。

应用会自动重启。重启后登录屏幕**多了一个选项**：除了 "Sign in with Anthropic" 还有 "Continue with Cowork on 3P"（或类似措辞），点这个进入第三方模式。

进去后正常对话。如果界面顶上显示你配的 model 名字，说明走通了。

### 7. 验证（可选）

**Help → Troubleshooting → Copy Managed Configuration Report**

会复制一段配置摘要到剪贴板，里面写：

- 哪些 key 被识别了
- 配置从哪读的（managed profile / 本地 config）
- 凭证有没有验证通过（密文已脱敏）

如果 Apply 后启动还是看到标准 Anthropic 登录页，没有 3P 选项，几种可能：

- `inferenceProvider` 没填或拼错
- 应用没完全退出就改了配置（彻底退出再启动）
- 凭证错了，看应用日志：
  - macOS: `~/Library/Logs/Claude/main.log`
  - Windows: `%APPDATA%\Claude\logs\main.log`

## 切回标准模式

登录屏幕选 "Sign in with Anthropic" 就回到正常 Anthropic 账号模式。本地的 3P 配置还在，下次想用回来直接选另一个选项。

要彻底清掉 3P 配置：

- macOS: 删掉 `~/Library/Application Support/Claude-3p/claude_desktop_config.json`
- Windows: 删掉 `%APPDATA%\Claude-3p\claude_desktop_config.json`

## Code 标签页

Claude Desktop 里有个 Code 标签页（内嵌 Claude Code）。3P 模式下，Cowork 的配置不会自动同步到 Code 标签。如果你想用 Code 标签也走第三方 API，需要单独给 Claude Code 配 `managed-settings.json`，或者干脆把 Code 标签关掉：

配置窗口的 **Sandbox & workspace** 区里，`isClaudeCodeForDesktopEnabled: false`。

## 常见坑

**Apply locally 之后没看到 3P 选项**
检查 Configuration Report，多半是 provider 字段没识别。Provider 名字是大小写敏感的：`Gateway` / `Vertex` / `Bedrock` / `Foundry`。

**模型列表不对**
Claude Desktop 会按你填的 model list 出下拉框。模型名要和后端 provider 接受的格式一致：CF Gateway 用 Anthropic 原始名（`claude-sonnet-4-5`），Bedrock 用 Bedrock 格式（`anthropic.claude-sonnet-4-5-20250929-v1:0`），Vertex 类似。

**网络层报错**
配置窗口的 **Egress Requirements** 区会列出当前配置需要打通的所有 host。本地装机基本不用管，企业网络环境下让 IT 把这些 host 加白名单。

**EDR 软件拦截**
Santa / CrowdStrike Falcon / Microsoft Defender ASR 这类终端安全软件可能会拦截 3P 模式下的 agent helper（位于 `~/Library/Application Support/Claude-3p/...` 或 `%APPDATA%\Claude-3p\...`）。让 IT 按 Anthropic 签名（macOS Team ID `Q6L2SF6YDW`、Windows publisher `Anthropic, PBC`）放行，比按路径放行稳。

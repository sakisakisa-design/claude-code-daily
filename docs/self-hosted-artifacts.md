# 自托管 Artifacts：Worker + D1 给 agent 一个自己的控制台

Claude Code 在 2026-06-18 上线了 Artifacts（beta）：把一次 coding session 发布成 claude.ai 上的一个私有页面。好用，但有三个硬约束：

1. **数据在 Anthropic 服务器上**。页面内容托管在 claude.ai。beta 期间只有 Team / Enterprise 能用，影响面还小；2026-07-04 起对个人订阅开放，当天各群就出现大量「Claude 下意识把 session 内容发布上去了」的案例——对不想把私人数据放第三方服务器的人是硬伤。
2. **CSP 全封网**：页面禁止一切 fetch / XHR / WebSocket，只能是静态快照，不能有持久状态。

这两条反过来就是自托管方案的需求清单：数据放自己域名下、页面可以读写自己的状态。整套东西一个 Cloudflare Worker（免费额度）就够了。本文是通用模式教程，照着做你会得到：一个手机上打开的私人控制台，agent 可以往里持续交付「会记住状态的小应用」。

## 架构

```
┌─────────────────────────────────────────────┐
│            Cloudflare Worker（一个）          │
├──────────────────┬──────────────────────────┤
│ GET /admin/<path> │ 静态托管：从 GitHub 仓库   │
│                  │ shell/ 目录读文件返回      │
│                  │ （contents API + 缓存）    │
├──────────────────┼──────────────────────────┤
│ GET/POST         │ 通用状态存取：D1 一张表     │
│ /api/<f>/state   │ 乐观锁版本号，token 鉴权    │
└──────────────────┴──────────────────────────┘
        ↑ git push 即部署页面        ↑ 页面 JS fetch
┌──────────────┐          ┌──────────────────┐
│ GitHub 仓库   │          │ 手机浏览器         │
│ shell/*.html │          │ （PWA 化随意）     │
└──────────────┘          └──────────────────┘
```

关键设计：**Worker 永远不改**。它只有两个通用能力——「把仓库目录当静态站」和「按 feature 名存取一个 JSON blob」。之后所有新功能都是 agent 往仓库 push 一个 HTML 文件，或多用一个 feature 名，Worker 零改动。这一点对 agent 协作特别重要：worker 一旦稳定就冻结，agent 再怎么折腾也只是在上面加页面，炸不了底座。

## D1：一张表存所有状态

```sql
CREATE TABLE feature_state (
  feature TEXT PRIMARY KEY,
  version INTEGER NOT NULL,
  data TEXT NOT NULL,        -- JSON blob
  updated_at TEXT NOT NULL
);
```

接口语义（Worker 里 ~60 行就能写完）：

- `GET /api/<feature>/state?token=...` → `{feature, version, data}`；不存在返回 404
- `POST` 同 URL，body `{version, data}`：
  - `version` 必须等于当前行的版本（乐观锁），成功后版本 +1
  - `version: 0` 且行不存在 → 创建新 feature，**这就是「加新功能不改后端」的机制**
  - 版本不匹配 → `409` + 当前版本，调用方重读重放

客户端约定：永远先 GET 拿最新 version 再 POST 整个 blob；409 就重来一次。单用户或夫妻档场景下这个粒度完全够用，不需要更细的并发控制。

## 页面规范（和官方 artifacts 同款约束，多一条豁免）

- **单文件 HTML**：CSS/JS 全部内联，无框架无 CDN 无外部字体。官方 artifacts 被 CSP 逼出来的格式，其实本来就是「agent 交付一个小应用」的最优原子——一个文件、一次 review、一次 push。
- **豁免条款**：可以 fetch 自己的 `/api/<feature>/state`。这是自托管版比官方版多出来的全部能力，也是质变所在：页面从「工作快照」变成「有记忆的小应用」。
- token 放 `localStorage`，多个页面共用同一个 key，登录一次全站通用。
- 所有动态内容过 `escapeHtml` 再进 innerHTML。
- 移动端优先：你最终 90% 是在手机上用它。

## 让 agent 施工：省钱流水线

主对话里的模型（贵）不写代码，只写规格和验收。实测好用的流水线：

1. **主 agent 写施工规格**：数据结构、交互流程、硬约束（只许加不许改、escapeHtml、无框架）、验收标准，一份 markdown。
2. **便宜模型施工**：把规格喂给低价位模型（子 agent、另一个 CLI 都行），产出完整文件。禁止它 commit。
3. **另一个子 agent 对抗性审查**：prompt 明确写「尽力 break 它」，列具体探针（XSS、空数据、竞态、移动端溢出、视图状态机），要求 BLOCKER/BUG/NIT 分级 + 复现场景 + 最小修复。
4. **施工方修复 → 审查方复验**（把审查结论原样发回施工 agent，再把修复摘要发回审查 agent 复验，两边都复用原上下文）。
5. 主 agent merge、push、线上 curl 验证。

一天下来的真实数据：两个功能（章节阅读器 + 转盘小游戏），审查各抓到一个真 bug（后台刷新不重绘已打开的视图；CJK 长标签在窄格子里溢出），全部修复复验后合并，主模型全程零行功能代码。

## 踩过的坑（每个都真实付过学费）

| 坑 | 症状 | 解法 |
|---|---|---|
| 强制暗色模式 | Android Chrome 把浅色页面反色成「赛博朋克」，图片却不反 | `<meta name="color-scheme" content="only light">` + CSS `:root { color-scheme: only light; }` |
| 相对路径 | 页面在 `/admin`（无尾斜杠）时，`href="slot.html"` 解析到根路径 404 | 站内一切导航和 fetch 全用绝对路径 `/admin/...` |
| 静态缓存 | push 之后手机上还是旧页面，以为没部署上 | contents API 前面留 `max-age=300`，改完等 5 分钟或带 `?cb=` 参数验证 |
| CJK 溢出 | 中文标签在固定高度小格子里换行溢出，串到相邻元素 | `-webkit-line-clamp` + `overflow:hidden` 双保险，按最长字符串做算术验证 |
| 公开目录 | 静态托管路径无鉴权，镜像到页面目录的内容全网可读 | 只镜像可公开的内容；私密数据一律走带 token 的 `/api` |

## 能拿它做什么

状态 API + 单文件页面这个组合，官方 artifacts 做不了的全在这里：

- **仪表盘**：任务板、习惯打卡、积分账本——agent 在对话里改状态，页面实时反映
- **阅读器**：长文档切块进仓库，页面做目录 + 进度 + 批注，和 agent 的共读进度同一份状态
- **小游戏/抽签转盘**：结果和历史落 D1，换设备不丢
- **任何「agent 是写入方、你是查看方」的场景**：agent 通过对话往状态里写，你随时打开页面看

## 成本

全部落在免费额度内：Workers 免费档 10 万请求/天，D1 免费档 5GB。域名可选（workers.dev 子域也行）。唯一的真实成本是让 agent 把 Worker 写出来的那半小时——而它写完就冻结了。

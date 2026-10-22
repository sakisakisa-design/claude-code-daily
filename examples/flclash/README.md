# FlClash 固定出口与日常分流模板

给 Mac 和 Android 各留一份可改的配置。Claude、Google、ChatGPT、支付和验证相关请求走 `Identity`，日常流量走 `Proxy`，自建备用和订阅备用分开手动选择。

**这里没有可用节点、订阅地址或代理服务。** 所有出口组都用 `REJECT` 占位，填好自己的节点后再用。未配置的代理业务会被拒绝；命中 `DIRECT` 的流量仍可直连，文件也无法管住没有进入代理或 VPN 的流量。

## 文件

| 文件 | 用途 |
| --- | --- |
| [macos.example.yaml](macos.example.yaml) | Mac 模板，包含 Claude 桌面进程规则，文件内 TUN 默认关闭 |
| [android.example.yaml](android.example.yaml) | Android 模板，使用 Claude、Google Play、Google Wallet 包名规则，文件内 TUN 开启 |
| [check_templates.py](check_templates.py) | 离线检查空模板、策略组引用与路由约束 |

两份模板都保留域名/IP 分流、固定出口 DNS、局域网直连、国内直连和日常代理规则。节点专属地址规则已经移除，加入自己的节点后按需补充。

## 先做本地副本

在这个目录运行，按设备选择一条。

```bash
cp macos.example.yaml macos.local.yaml
cp android.example.yaml android.local.yaml
```

`.local.yaml`、`.local.yml`、代理集合缓存和 `.venv` 已加入本目录的忽略规则。只在本地副本里填写节点、UUID、密码和订阅令牌，不要改完公共示例再提交。忽略规则无法保护已经被 Git 跟踪的文件。

## 填写节点

把本地副本的 `proxies: []` 换成自己的节点列表。下面只演示字段位置，使用自己的服务端配置替换示例值；Reality、WebSocket 等传输参数也必须与服务端一致。

```yaml
proxies:
  - name: FixedExit
    type: vless
    server: proxy.example.invalid
    port: 443
    uuid: REPLACE_WITH_YOUR_UUID
    network: tcp
    tls: true
    servername: tls.example.invalid
```

在 `proxy-groups` 里找到已有的 `Identity` 和 `Auto`，分别把 `proxies: [REJECT]` 改成 `proxies: [FixedExit]`，不要追加同名策略组。这样固定出口与日常主力都能使用该节点。

有第二个入口时，确认它实际通向哪个公网出口，再决定是否加入 `Identity`。相同 UUID、节点名或配置文件不能证明出口相同。`Identity` 保持手动选择，不接入机场测速组或直连兜底。

自建备用放进 `SelfHosted-Backup`。需要时先在这个组里选节点，再到 `Proxy` 里选 `SelfHosted-Backup`。备用不会混进主力 `Auto`。

## 填写订阅

把本地副本的 `proxy-providers: {}` 换成自己的代理集合定义。地址仅使用占位域名。

```yaml
proxy-providers:
  my-subscription:
    type: http
    url: https://subscription.example.invalid/clash.yaml
    path: ./proxy_providers/my-subscription.yaml
    interval: 21600
    proxy: DIRECT
    header:
      User-Agent:
        - clash.meta
    health-check:
      enable: false
      url: https://www.gstatic.com/generate_204
      interval: 600
      lazy: true
    override:
      additional-prefix: "[Subscription] "
```

再把已有的 `Subscription-Backup-1` 改成下面这样，删除它原来的 `REJECT` 占位。

```yaml
- name: Subscription-Backup-1
  type: select
  use:
    - my-subscription
```

多个订阅使用不同的集合名、缓存路径和节点名前缀。第二个订阅可接到 `Subscription-Backup-2`，更多来源可以自行添加组，并把组名加入 `Proxy`。

示例每六小时更新订阅，不开启后台批量测速。`proxy: DIRECT` 只指定集合下载使用的连接方式，避免下载依赖它自己的节点。某些网络可能无法直连订阅站，此时需要另选一个独立可用的下载策略，不要指回依赖该订阅的组。

代理集合只提供节点，不采用订阅下发的整份 DNS、规则和策略组。这样刷新节点不会把本地分流替换掉。优先使用 HTTPS 订阅；URI/Base64 来源还依赖所用 mihomo 版本的转换能力。

## Mac 导入与端口

从文件导入 `macos.local.yaml`，使用规则模式，先保留旧配置方便回退。

模板混合端口为 `7890`，只绑定本机且不开放局域网共享。FlClash 的全局端口设置可能覆盖文件，系统代理、环境变量和软件独立代理也可能各用不同端口。迁移客户端时先确认实际监听，再统一修改需要使用它们的程序。

```bash
scutil --proxy
lsof -nP -iTCP:7890 -sTCP:LISTEN
```

文件内 TUN 默认关闭。只启用系统代理时，部分原生 TCP/UDP、独立解析和未遵循系统代理的应用可能不被接管。是否启用 TUN、如何接管系统 DNS，需要在 App 中根据环境设置。

磁盘上的本地副本修改后，App 内已导入的配置不一定同步更新。重新导入或在 App 内明确更新，再检查当前配置和各组选择。`store-selected` 可能恢复旧的选中项。

## Android 导入与 VPN

从文件导入 `android.local.yaml`，选择规则模式，启动 FlClash VPN 并授予系统权限。YAML 中的 `tun.enable` 不能替代 App 创建 VpnService。

包名规则覆盖 `com.anthropic.claude`、`com.android.vending` 和 `com.google.android.apps.walletnfcrel`。相关 App 与用于登录、验证的浏览器必须被 VPN 接管，检查分应用代理和绕过列表，开启查找进程功能。

包名识别依赖 Android、FlClash 和 mihomo 的版本与权限，共享 UID、浏览器登录及委托给其他服务的流量也可能超出这三个包名。保留的域名规则提供补充，无法据此保证每一条业务流量都被固定。

检查 Android 私人 DNS、浏览器安全 DNS及其他 App 自带 DoH。端口 53 接管无法覆盖 DoT 或 HTTPS DNS。模板关闭了顶层与 DNS IPv6，但最终的 IPv6、DNS 和路由行为仍由 App 与系统设置共同决定。

Android 通常只有一个活动 VpnService，不要假定 FlClash 能与 Tailscale、WARP 等 VPN 同时叠加运行。

## 两处需要按自己的网络判断

### 固定出口 DNS

普通真实 DNS 查询通过 `Identity`，节点地址解析使用独立的引导解析路径，局域网名称保留 `system` 例外。检查 App 的 DNS、规则和脚本覆写，避免覆盖文件。

选择日常备用不会切换 `Identity`。如果固定出口完全不可用，依赖它的 DNS 也可能失败，即使备用节点本身能连通。这份模板不提供全业务自动故障转移。

### Tailscale 与家庭网络

模板保留了自定义路由，`tailscale.com`、`tailscale.io`、`ts.net` 和 `100.64.0.0/10` 走 `Proxy`，常见家庭私网走 `DIRECT`。这种设置要求远端代理本身有权访问目标 tailnet，普通订阅节点不会自动获得该权限，公共 DoH 也不能提供私有 MagicDNS 记录。

不需要这种远端代理方式时，导入前按自己的网络调整这些规则与 DNS 策略；不要把它当成所有 Tailscale 用户的默认方案。

## 核对与回退

先确认本地节点配置完整、App 中实际生效的端口与接管方式，再使用普通出口检测站核对。模板中的 `webshare.io`、`api.ipify.org` 等明确走 `Identity`，所以切换 `Proxy` 后它们仍可能显示固定出口。

检测站的结果只说明当次请求的路径，无法证明所有 App、DNS、IPv6 和 VPN 外流量都走同一路径，也无法证明节点属于住宅 IP。模板不保证账号登录、地区验证或支付可用。

不需要发起 Claude、Google 登录或支付请求来做配置静态检查。导入失败时回到旧配置，反馈报错前先隐藏订阅链接、令牌和节点凭据。

## 离线检查

需要 Python 3 和 PyYAML，下面的检查不会连接订阅、节点或业务服务。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python check_templates.py
```

检查针对提交的空模板，填写过真实节点的本地副本不属于它的测试目标。目前没有完成这些公开模板的实际内核加载或 Android 真机验证。

## 参考

参考了 [one-exit](https://github.com/wquguru/one-exit) 的固定出口分流思路及 Android 包名规则。该项目的住宅 HTTP 链需要用户另行提供代理凭据，本目录不包含住宅服务、链式中转或其覆写脚本。不要直接叠加含占位节点的原版脚本。

配置字段以 [mihomo 文档](https://wiki.metacubex.one/) 为准，App 覆写和 VPN 行为参照所使用的 [FlClash 版本](https://github.com/chen08209/FlClash)。

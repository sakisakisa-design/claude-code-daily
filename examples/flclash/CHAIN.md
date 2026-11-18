# FlClash 链式代理：机场接入，自建 VPS 出口

适合「直连自建 VPS 慢，但机场线路快；同时又希望 Claude 等业务保持固定出口」的情况。先用 [Android 链式模板](android-chain.example.yaml) 做本地副本：

```bash
cp android-chain.example.yaml android-chain.local.yaml
```

公开模板没有节点和订阅，`Entry`、`FixedExit` 都以 `REJECT` 占位。以下修改只写入本地副本；不要把自己的订阅令牌、节点密码、UUID、私有域名或 tailnet 地址提交到仓库。

## 1. 先看清两跳

```text
手机 → 手动选择的机场节点（Entry）→ 自建 VPS（FixedExit）→ 目标网站
```

机场改善手机到 VPS 的接入路径；目标网站看到的是自建 VPS 的公网 IP。机场能看到它在连接 VPS，HTTPS 业务内容仍受自身加密保护。链式多了一跳，是否更快取决于实际线路；客户端显示的延迟不一定包含最终网站的完整耗时。

模板只保留四个选择组：

| 组 | 作用 |
| --- | --- |
| `Entry` | 手动选一个机场节点；机场直出和链式共用它，没有自动测速组 |
| `FixedExit` | 选自建 VPS 节点，节点通过 `Entry` 拨号；没有机场或直连自动兜底 |
| `Claude` | 默认 `FixedExit`，需要时可手动切 `Entry`；切换会改变该业务出口 |
| `GPT` | 与 `Claude` 独立选择，默认 `FixedExit` |

国内与局域网直连，视频流媒体走机场；普通海外 TCP、业务 DNS 和明确的固定出口规则走 VPS。其他海外 UDP 走机场，详见第 4 节。

## 2. 把自建节点接到机场入口

把 `proxies: []` 换成自己的 VPS 节点。下面用 Shadowsocks 演示 `dialer-proxy` 的位置；协议、端口、加密方式和密码都要与自己的服务端一致。

```yaml
proxies:
  - name: VPS-Chain
    type: ss
    server: vps.example.invalid
    port: 443
    cipher: chacha20-ietf-poly1305
    password: REPLACE_WITH_YOUR_PASSWORD
    udp: false
    dialer-proxy: Entry
```

再把已有 `FixedExit` 的 `proxies: [REJECT]` 改成 `proxies: [VPS-Chain]`，不要新增同名组。

关键是 **`dialer-proxy` 写在自建节点上，值是机场选择组**。不要反过来把机场节点接到 VPS，也不要在机场集合的 `override` 中加入 `dialer-proxy: FixedExit`，否则会形成循环。

这份教程按自建节点只承载 TCP 来设计，UDP 另行分流。AnyTLS、VLESS/Reality 等可以按自己的服务端填写，但是否能穿过所选机场必须实际验证。mihomo 文档建议链式先从简单协议开始，UDP 底层协议与某些伪装协议可能不兼容；不要直接复制别人的传输参数或关闭证书验证。

## 3. 订阅需要代理，第一次如何启动？

只配置「订阅下载走订阅自己的节点」会遇到冷启动循环：没有节点就下载不了，下载不了又没有节点。做法是给集合内置至少一个当前可用的机场节点作为 `payload`，先建立链路，再更新订阅。

把 `proxy-providers: {}` 替换为下面的结构。`payload` 里的节点取自自己的现有订阅，使用真实协议字段替换示例。

```yaml
proxy-providers:
  airport:
    type: http
    url: https://subscription.example.invalid/clash.yaml
    path: ./proxy_providers/airport.yaml
    interval: 86400
    proxy: FixedExit
    header:
      User-Agent:
        - clash.meta
    health-check:
      enable: false
      url: https://www.gstatic.com/generate_204
      interval: 600
      lazy: true
    payload:
      - name: Airport-Bootstrap
        type: ss
        server: entry.example.invalid
        port: 443
        cipher: chacha20-ietf-poly1305
        password: REPLACE_WITH_AIRPORT_PASSWORD
        udp: true
```

把已有 `Entry` 组替换为：

```yaml
- name: Entry
  type: select
  use:
    - airport
```

删除它原来的 `proxies: [REJECT]`。示例里的 `udp: true` 仅表示客户端启用 UDP，机场服务端也必须支持，不能靠改一个字段获得能力。

导入后先在 `Entry` 里选可用节点，`FixedExit` 里选 `VPS-Chain`，再更新集合。下载路径为「机场 → VPS → 订阅服务器」；如果订阅只需机场即可下载，也可把集合的 `proxy` 改成 `Entry`，同样需要冷启动 `payload`。订阅本身可直连时，独立使用 `DIRECT` 也是选择。

集合每天更新；正常下载的节点优先使用，内置备用不会自己变新。机场节点坏了，手动换入口后再更新。缓存为空、下载失败时仍需有可用的备用节点；如果所有备用都失效，要借助另一份能联网的配置重新取得节点。FlClash 的订阅资源/代理集合页面可以手动更新集合，本地文件无需填写远程配置地址。

只读取订阅的节点，保留本地 DNS 和规则。不要直接导入机场的整份配置覆盖本模板。首次导入时还需要能取得 mihomo 使用的 GeoSite/GeoIP 数据；内置节点不能替代这些规则数据。

## 4. UDP：只拦 Claude，不全局一刀切

模板的顺序是：

1. 拦截 Claude 安卓包名 `com.anthropic.claude` 与 Claude/Anthropic 域名的 UDP，让支持回退的连接改走 TCP。
2. 保持 Tailscale 目标 UDP 拒绝连接，因为本教程的固定 VPS 路径未启用 UDP。
3. 局域网和国内其他 UDP 直连，其他海外 UDP 明确交给 `Entry`。
4. TCP 再按 Claude、GPT、固定出口和流媒体等规则分流。

没有全局 `NETWORK,UDP,REJECT`，也不会因为某个节点未启用 UDP 就假设它能透明回退。ChatGPT 语音、其他通话或游戏能否恢复，还取决于所选机场节点的 UDP 能力。海外 UDP 的最终出口是机场，**不保证与 VPS 的 TCP 出口一致**；不要把这版称为「所有流量统一出口」。

安卓包名拦截需开启进程识别并实际命中。用 Brave 等浏览器打开 Claude 时，第三方 STUN/TURN 流量可能只有 IP 或第三方域名，无法按 Claude 页面归属识别。这版不拦整个浏览器；需要额外限制 WebRTC 时，在浏览器里使用其防止非代理 UDP 的选项（如版本提供），并在手机上用泄漏检测页核验。域名分流不能证明 WebRTC 已无泄漏。

### Claude 的 Datadog 遥测

`http-intake.logs.us5.datadoghq.com` 是 Claude Code 官方网络文档列出的运行遥测端点。本模板显式把它的 TCP 请求交给 `Claude` 组；对应 UDP 先被 Claude 专属规则拒绝。旧模板的 `DOMAIN-SUFFIX,datadoghq.com,Identity` 已覆盖它，精确规则是为了让它跟随独立的 Claude 选择。

文档确认的是 Claude Code 的用途，不能据此认定所有 Claude 客户端都调用它。它属于可选遥测；如需要在 Claude Code 关闭非必要流量，可使用官方的 `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`，无需把整个 Datadog 服务拒绝连接。

## 5. DNS、手机 VPN 与 Tailscale

业务 DNS 经固定 VPS 使用 DoH；代理节点域名使用独立直连 DoH 引导解析，局域网名称有 `system` 例外。启用 Android VPN/TUN 与规则模式，将相关应用和登录浏览器纳入 VPN，检查 FlClash 的 DNS/规则覆写，关闭追加系统 DNS。Android 私人 DNS、浏览器自带 DoH 也要单独检查；53 端口接管管不到自带的 HTTPS DNS。按需要开启 Android「始终开启 VPN」和「阻止未使用 VPN 的连接」。

模板关闭 IPv6 并拒绝进入内核的 IPv6 流量，但仍需确认 App 没有覆写这些设置。这里只处理经过 FlClash 的流量。

Tailscale 规则优先将 `100.64.0.0/10` 和 `ts.net` 交给固定 VPS。**VPS 自身必须加入目标 tailnet 并拥有访问权限**；这是通过远端 VPS 访问组网，手机无需同时启动另一个 Tailscale VPN。公共 DoH 不能解析私有 MagicDNS：在本地副本 `hosts` 中填写自己的完整设备域名与组网 IP；使用短名称时也补上短名称，并添加 `DOMAIN,自己的短名称,FixedExit` 规则，放在局域网规则前。不要提交真实设备信息。

先在 VPS 上测目标 IP、Tailscale ping 和实际服务，再测手机。组网显示在线不代表 SSH/网页服务可达。若不需要这条远端访问路径，请自行调整 Tailscale 规则；不要将其改为失败后自动机场直出。

Mac 用户可参考同一条 `dialer-proxy` 链路，结合 [原 Mac 模板](macos.example.yaml) 的进程规则。Android 的包名和 VPN 行为不适用于 Mac；只开系统 HTTP 代理也接管不了全部 UDP。

## 6. 验证与回退

```bash
python3 check_templates.py
# 已安装 mihomo 时，先验证填写后的本地副本：
mihomo -t -d /你的/mihomo数据目录 -f android-chain.local.yaml
```

分两层核对：先确认 FlClash 当前启用的是新文件及规则模式，再在连接详情中检查机场首跳和 VPS 节点链，使用 `api.ipify.org` 等被模板固定分流的检测站确认最终 VPS IP。只看到 VPS 出口不能证明机场首跳也已使用；切换 `Claude` 不会改变检测站固定走 `FixedExit` 的规则，要在连接详情看 Claude 的实际路径。

在可回退的独立测试环境测试「无缓存且订阅下载失败」时 `payload` 节点仍出现，再确认正常更新与手动切换；不要为测试删除日常配置或唯一可用缓存。还需在手机分别检查 DNS、IPv6、WebRTC、语音/游戏和私网服务。

公开空模板经过离线脚本和 mihomo 配置加载检查；这是语法、引用和路由约束验证，没有用这些占位节点联网。机场到 VPS 的方案已有私人部署实测，但不能替代读者自己的节点、设备和 FlClash 版本验证。改完磁盘文件后应重新导入或明确更新 App 内配置，保留旧文件方便回退。

## 参考

- [mihomo dialer-proxy：通过订阅节点中转自己的 VPS](https://wiki.metacubex.one/en/config/proxies/dialer-proxy/)
- [代理集合与 payload](https://wiki.metacubex.one/en/config/proxy-providers/)
- [mihomo 规则优先级与逻辑规则](https://wiki.metacubex.one/en/config/rules/)
- [Claude Code 网络与遥测端点](https://code.claude.com/docs/en/network-config)

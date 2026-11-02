# 多机场优选订阅 · 实时版 v3

> **节点列表 10 秒一刷 · 每个节点 10 秒一测 · 出问题才换节点 · 站点可独立指定**
> 全部节点在本机 mihomo 内核真实拨号验证，出口 IP 逐条核对，假节点已剔除

---

## 🥇 本机实时源 —— 用这一条（FlClash / Mihomo / Clash Verge）

```
http://127.0.0.1:18888/clash.yaml
```

本机 watcher 常驻进程提供的订阅入口，**没有 CDN、没有缓存、没有 FlClash 的 20 分钟定时器**。
导入一次，之后节点列表由内核自己每 10 秒重拉，永久不用手动更新。

| 谁在刷新 | 刷什么 | 频率 | 配置依据 |
| --- | --- | --- | --- |
| 你的内核 | 从 `/live-provider.yaml` 重拉节点列表 | **10 秒** | `proxy-providers.live.interval: 10` |
| 你的内核 | 对每个节点做健康检查 | **10 秒** | `health-check.interval: 10`, `lazy: false` |
| 你的内核 | 节点连续 3 次探测失败才判死 | 即时 | `max-failed-times: 3`（双向防抖：失败要 3 次，复活也要 3 次） |
| `⭐ 智能选择` | 粘住当前节点，**只在它挂了才顺延** | 故障时 | `fallback` 语义 |
| 本机 watcher | 全量重拉 9 家机场订阅 + 重测 | **30 分钟** | 慢循环 |
| 本机 watcher | 只重测当前池 40/80 节点 | **10 秒** | 快循环 |

**实测收敛数据**：FlClash 的 provider 缓存文件 `cacheAge` 恒为 **2 秒**，
即本机源一发布，内核一轮内就拿到（对比 GitHub raw 固定路径的历史实测是 **175 秒**）。

> **为什么必须用本机源**：`raw.githubusercontent.com` 对固定路径的缓存是 `max-age=300`，
> 12 个公共镜像实测 push 后 284 秒内只有 1/12 拿到新内容。而 provider 的 URL 必须固定，
> 所以「GitHub 镜像 + provider」这条路做不出 10 秒级实时性——只有本机 HTTP 源可以。

### 三个版本的分工（别混用）

| 版本 | 链接 | provider 源 | 拉取间隔 | 适用 |
| --- | --- | --- | --- | --- |
| **本机版** | `http://127.0.0.1:18888/clash.yaml` | 本机 watcher | **10 秒** | 就在这台电脑上用（FlClash/Clash Verge） |
| **远端版** | `proxy-sub/clash-live-provider.yaml` | GitHub raw | 300 秒 | 另一台电脑/外网 |
| **手机版** | `http://127.0.0.1:18888/clash.yaml`（经 adb reverse） | 本机 watcher | **10 秒** | Android 手机（adb 连着这台电脑时） |

远端版受 raw CDN `max-age=300` 限制，写 10 秒也没意义（每次拉到的是同一份缓存）。
**三个文件由同一个 watcher 生成，节点内容一致。**

### 本机源的其它路由

| 路由 | 内容 |
| --- | --- |
| `/clash.yaml` 或 `/clash` | **主入口**，provider 版完整配置（13 组 + 42 条规则），每次请求都是内存里最新那份 |
| `/clash-live.yaml` | 同上（历史别名，内容与 `/clash.yaml` 逐字节一致） |
| `/live-provider.yaml` | 纯 `proxies:` 段，给主配置里的 provider 拉取用（40 节点） |
| `/live.txt` | base64 订阅，给 v2rayN / NekoBox / Shadowrocket |
| `/health` | `{"gen":N,"at":时间戳,"providerBytes":字节数}`，`gen` 每轮发布 +1 |

所有响应都带 `Cache-Control: no-store`，不存在任何中间缓存。
主配置不再读磁盘文件，而是直接用 watcher 内存里的成品——池子变化时不会再出现「组和节点对不上」。

---

## 🎯 选路语义：什么叫「非必要不切换」

`⭐ 智能选择` 和 4 个国家组都是 **`fallback`** 类型，行为是：

> 取成员列表里第一个健康的节点；**之后只要它还健康，就永远不换**。
> 只有它真的挂了，才顺延到下一个。

这和 `url-test` 有本质区别——`url-test` 永远追最快的，延迟抖 1ms 就换一个，看起来就是「节点一直在跳」。
本方案里 `url-test` 只保留了一个 `🔥 最快节点` 组给「我要速度不要稳定」的场景，默认链路不走它。

### 实测（本机隔离内核，12 次采样 / 5 秒间隔）

```
#01 now=🇸🇬 SG🍉新加坡3  exit=140.235.141.169
#02 now=🇸🇬 SG🍉新加坡3  exit=140.235.141.169
...
#12 now=🇸🇬 SG🍉新加坡3  exit=140.235.141.169
```

60 秒内节点零变化、出口 IP 零变化。把节点人为掐死后，同一国家组内的下一个节点会接上，
**而不会换到别的国家**——这正是「选新加坡就一直用新加坡」的效果。

### 节点顺序为什么必须锁死

`fallback` 每次 provider 内容更新都会**重置选择**：实测把 provider 顺序从正序改成反序后，
组的选择立刻从 `SG🍉新加坡3` 变成新的第一个成员。
所以 watcher 用 `order.json` 锁定节点顺序，新节点只追加到末尾，**快循环绝不重排**。

---

## 🗂 组结构（13 组）

| 组 | 类型 | 说明 |
| --- | --- | --- |
| `⭐ 智能选择` | fallback | **默认出口**，全局最粘，40 节点里挑第一个健康的 |
| `🔥 最快节点` | url-test | 手动切到这里才用；`tolerance: 50` 抗抖，10 秒重测 |
| `🇭🇰 香港` / `🇹🇼 台湾` / `🇯🇵 日本` / `🇸🇬 新加坡` | fallback | 国家组，组内粘性；某国节点掉光就不生成该组 |
| `🤖 AI 服务` | select | → 港/台/日/新/美 国家组 |
| `🎬 Netflix` | select | → 港/台/日/新 国家组 |
| `📺 动画疯` | select | → 只给 台湾（巴哈姆特仅对台湾 IP 开放） |
| `🛒 Google Play` | select | → 港/台/日/新/美 国家组 |
| `🔀 手动切换` | select | 组 + 全部节点 + DIRECT 的入口，想钉死某个节点用这里 |
| `🎯 直连` / `🛑 拦截` | select | — |

**站点组为什么是 `select` 而不是 `fallback`**（设计要点，别改）：

- `fallback` **不探测策略组成员**——成员写成组名，内核就当它「存活」，永远不回落；
- `fallback` 的 `use` + `filter` 只能平铺节点，按地区平铺后 AI/Netflix/GooglePlay 三组都是 38/40 成员，等于没有；
- `select` 的**用户选择在 provider 重载后会被保留**，`fallback` 会被重排结果覆盖。

所以链路是：`站点 → 站点组(select) → 国家组(fallback) → 粘在同一个节点上`。

### 站点分流实测（本机隔离内核，走默认指向的 香港 组）

| 站点 | 结果 |
| --- | --- |
| `api.openai.com/v1/models` | **401**（= 可达未鉴权，没被地区封） |
| `chatgpt.com` | **403**（Cloudflare 对机房 IP 的正常拦截，换个节点可解） |
| `netflix.com/title/…` | **301**（正常跳转） |
| `ani.gamer.com.tw/ajax/getdeviceid.php` | **200**（台湾 IP 通过） |
| `play.google.com/store` | **302**（正常跳转） |

40/40 节点 `api.openai.com` 全部返回 401、`play.google.com` 全部 200，
说明「能不能上」不是问题，重点是**别被 `GEOIP,CN` 判成直连**——所以这些域名规则排在 CN 判定之前。

---

## 📱 FlClash 怎么用（重要）

FlClash 的订阅自动更新被**硬编码为 20 分钟**
（`lib/application.dart:118-127`：`Timer(const Duration(minutes: 20), ...)`；
`auto_update_duration_millis` 虽然参与判断，但被这个固定节拍卡住，改 DB 设成 60 秒也无效）。
**所以普通订阅链接在 FlClash 里最快也是 20 分钟才换一批节点。**

绕过方式就是 provider 架构：FlClash 会把 YAML 里的 `proxy-providers` 段**原样传给内核**，
只把 `path` 改写到自己的缓存目录，`interval` 照常生效。

本机实测确认（FlClash `0.9.2+2026102401`）：

- provider 缓存路径 `…\com.follow\clash\profiles\providers\<profileId>\proxies\<md5>`
- 运行时配置 `proxy-providers.live.url = http://127.0.0.1:18888/live-provider.yaml`，`interval = 10`
- 缓存文件 mtime 严格按 10 秒节拍重写 —— **20 分钟限制被完全绕过**

**导入步骤**：FlClash → 配置 → 添加 → URL → 填 `http://127.0.0.1:18888/clash.yaml` → 确定 → 启用。
或直接点：`flclash://install-config?url=http://127.0.0.1:18888/clash.yaml`

> 前提：本机 watcher 进程在跑（见下方「本机运维」）。不在跑时本机源会连不上，
> 此时退回 GitHub 静态链接，但刷新会退回 5 分钟 / 20 分钟级别。

---

## 🌐 GitHub 静态链接（备用，不需要本机进程）

前缀 `https://raw.githubusercontent.com/VnchowWang/test/main/`

| 用途 | 路径 | 刷新 |
| --- | --- | --- |
| **推荐备用**：provider 版主配置（v3，13 组） | `proxy-sub/clash-live-provider.yaml` | 内容每 5 分钟由 watcher 重写 |
| 完整版：内嵌节点，v3 组结构 | `proxy-sub/clash-live.yaml` | 每 5 分钟整份重写 |
| 静态版：62 节点 + ACL4SSR 全量规则（不自动更新） | `proxy-sub/clash.yaml` | 不更新 |
| v2rayN / NekoBox / Shadowrocket（base64） | `proxy-sub/live.txt` | 每 5 分钟重写 |
| 明文节点列表 / 测量元数据 | `proxy-sub/nodes.txt` · `proxy-sub/meta.json` | 每 5 分钟 |

远端版已实测：内核能独立从 raw 拉到 40 节点、13 组全部有成员、真实拨号 `204 / 0.15s`。

### 加速镜像

| 镜像 | 状态 |
| --- | --- |
| `https://ghproxy.net/https://raw.githubusercontent.com/…` | ✅ 200，字节数一致 |
| `https://gh-proxy.com/https://raw.githubusercontent.com/…` | ✅ 200，字节数一致 |
| `https://cdn.jsdelivr.net/gh/VnchowWang/test@main/…` | ⚠️ 有旧缓存，`@main` 不保证最新，建议带 commit sha |
| `raw.gitmirror.com` / `cdn.statically.io` | ❌ 不可用 |

### 订阅转换器

公开转换器**只认 `target=clash` 与 `target=mixed`**，`sing-box`/`v2ray` 返回 `Invalid target!`。
且本仓库的 raw 源被多数转换器拒（HTTPS 校验/超时），需用 jsDelivr 转发源。
结论：**能用原生 Clash 配置就别过转换器**。

---

## 🧭 节点命名与池子

命名格式：`机场｜🇸🇬国家NN｜NF+GPT+YT｜XXms`

- `机场` — 来源机场（渔云 CloudFisher / jisu / Stardream / 山水云 / 友连 / MuaCloud）
- `🇸🇬国家NN` — 出口落地国家与序号
- `NF+GPT+YT` — 实测解锁能力（Netflix / ChatGPT / YouTube）
- `XXms` — 发布时刻的实测延迟

**池子构成**：9 家机场订阅全量拉取（约 237 节点）→ 剔除「剩余流量/到期时间/官网」类信息伪节点
→ 全量拨号验证 → 存活约 146 → 按评分取前 80 进池 → 每轮发布 40 个最优。

**评分模型**：延迟（40%）+ 稳定性抖动（25%）+ 吞吐（20%）+ 解锁能力（15%），
已剔除出口 IP 与直连相同的假节点。

> 池子里有节点的国家才生成国家组（少于 2 个成员也不生成，因为无容错）。
> 当前池 40 节点的分布：🇭🇰 香港 15 / 🇹🇼 台湾 11 / 🇯🇵 日本 7 / 🇸🇬 新加坡 6，其余散点。

---

## 🛠 本机运维

```bash
# 看状态
curl -s --noproxy '*' http://127.0.0.1:18888/health
tail -20 "D:/Users/wangwenchao/Documents/deepseek-harness/default-workspace/work/watcher/watcher.log"

# 手动起（正常由计划任务自愈，不需手动）
schtasks //Run //TN ProxyLiveWatcher

# 手动重新生成主配置（改完 mk-main2.cjs 后）
cd work/watcher && TARGET=local POOL=live-provider.yaml node mk-main2.cjs pub-main.yaml
cd work/watcher && TARGET=remote POOL=live-provider.yaml node mk-main2.cjs clash-remote.yaml
```

- watcher 脚本：`work/watcher/proxy-live-watcher.cjs`
- 主配置生成器：`work/watcher/mk-main2.cjs`（**唯一生成路径**，watcher 里 `require` 它当模块用）
- 节点顺序锁：`work/watcher/order.json`
- 自愈：计划任务 `ProxyLiveWatcher`（登录触发 + 每 5 分钟检查，单实例守卫探 `/health` 防重复）
- 探测内核端口 `19440`(API) / `17940`(mixed)，本机源端口 `18888`
- 日志 `watcher.log`（快循环每 10 秒一行：`#N 活=X/80 已发布=Y`）

---

## ⚠️ 已知限制

1. **FlClash 无 `external-controller`**（它会把配置里这个键强制清空），
   所以无法从外部用 API 驱动 FlClash 的内核，切换只能靠内核自身的 `fallback`/`url-test`。
2. **Candytally / llG-New / LIME 三家订阅已失效**（403 / DNS 失败 / 非 YAML），池子里不含它们。
3. 端口 `18888` 被占用时 watcher 会在日志里报 `!! serve 端口错误`，本机源不可用，GitHub 静态链接不受影响。
4. 本机源只监听 `127.0.0.1`，**不对局域网/外网开放**（实测 AP 隔离导致手机 ping 不通本机）。
5. **手机走 adb reverse**：`adb reverse tcp:18888 tcp:18888` 把手机的 `127.0.0.1:18888` 映射到这台电脑，
   手机 FlClash 导入同一条链接即获得与电脑同样的 10 秒实时性。
   保活脚本 `work/phone/adb-reverse-keepalive.cmd`，计划任务 `AdbReverse18888` 每分钟检查。
   代价：**手机必须连着本机 adb**（USB 或同网 adb over WiFi）；拔线后请改用远端版链接。

---

_节点均为本机实测通过后发布；订阅内容含各机场节点凭证，仅个人使用。_

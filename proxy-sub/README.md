# 多机场优选订阅 · 实时版

> **节点列表 10 秒一刷、每个节点 10 秒一测、不可用立刻切换**
> 全部节点在本机 mihomo 内核真实拨号验证，出口 IP 逐条核对，假节点已剔除

---

## 🥇 本机实时源 —— 用这一条（FlClash / Mihomo / Clash Verge）

```
http://127.0.0.1:18888/clash.yaml
```

这是本机 watcher 常驻进程提供的订阅入口，**没有 CDN、没有缓存、没有 20 分钟定时器**。
导入一次，之后节点列表由内核自己每 10 秒重拉，永久不用手动更新。

| 谁在刷新 | 刷什么 | 频率 | 配置依据 |
| --- | --- | --- | --- |
| 你的内核 | 从 `/live-provider.yaml` 重拉节点列表 | **10 秒** | `proxy-providers.live.interval: 10` |
| 你的内核 | 对每个节点做健康检查 | **10 秒** | `health-check.interval: 10`, `lazy: false` |
| 你的内核 | `⭐ 优选集` 重挑最快节点 | **10 秒** | `interval: 10`, `tolerance: 0`（0 容差=慢一点就换） |
| 你的内核 | 单节点连续 2 次失败即出局 | 即时 | `max-failed-times: 2` |
| 本机 watcher | 全量重拉 9 家机场订阅 + 重测 | **30 分钟** | 慢循环 |
| 本机 watcher | 只重测当前池 40/80 节点 | **10 秒** | 快循环 |

**实测收敛数据**：`FlClash` 的 provider 缓存文件在采样中 `cacheAge` 恒为 **2 秒**，
即本机源一发布，内核一轮内就拿到（对比 GitHub raw 路径的历史实测是 **175 秒**）。

> **为什么必须用本机源**：`raw.githubusercontent.com` 对固定路径的缓存是 `max-age=300`，
> 12 个公共镜像实测 push 后 284 秒内只有 1/12 拿到新内容。而 provider 的 URL 必须固定，
> 所以「GitHub 镜像 + provider」这条路做不出 10 秒级实时性——只有本机 HTTP 源可以。

### 两个版本的分工（别混用）

| 版本 | 链接 | provider 源 | 拉取间隔 | 适用 |
| --- | --- | --- | --- | --- |
| **本机版** | `http://127.0.0.1:18888/clash.yaml` | 本机 watcher | **10 秒** | 就在这台电脑上用（FlClash/Clash Verge） |
| **远端版** | `proxy-sub/clash-live-provider.yaml` | GitHub raw | 300 秒 | 手机/另一台电脑/外网 |

远端版受 raw CDN `max-age=300` 限制，写 10 秒也没意义（每次拉到的是同一份缓存）。
本机版没有 CDN，才能做到 10 秒。**两个文件都由同一个 watcher 生成，节点内容一致。**

### 本机源的其它路由

| 路由 | 内容 |
| --- | --- |
| `/clash.yaml` | **主入口**，provider 版完整配置（9 组 + 12 条抗死锁规则） |
| `/live-provider.yaml` | 纯 `proxies:` 段，给主配置里的 provider 拉取用（40 节点） |
| `/clash-live.yaml` | 内嵌版完整配置（节点写死在文件里，每轮整份替换） |
| `/live.txt` | base64 订阅，给 v2rayN / NekoBox / Shadowrocket |
| `/health` | `{"gen":N,"at":时间戳,"providerBytes":字节数}`，`gen` 每轮发布 +1 |

所有响应都带 `Cache-Control: no-store`，不存在任何中间缓存。

---

## 📱 FlClash 怎么用（重要）

FlClash 的订阅自动更新被**硬编码为 20 分钟**
（`lib/application.dart:118-127`：`Timer(const Duration(minutes: 20), ...)`，
且 `auto_update_duration_millis` 虽然会参与判断，但被这个固定节拍卡住，
改 DB 设成 60 秒也无效）。**所以普通订阅链接在 FlClash 里最快也是 20 分钟才换一批节点。**

绕过方式就是上面的 provider 架构：FlClash 会把 YAML 里的 `proxy-providers` 段
**原样传给内核**，只把 `path` 改写到自己的缓存目录，`interval` 照常生效。

已在本机实测确认（FlClash `0.9.2+2026102401`）：

- provider 缓存路径 `…\com.follow\clash\profiles\providers\375526901701152768\proxies\<md5>`
- 运行时配置里 `proxy-providers.live.url = http://127.0.0.1:18888/live-provider.yaml`，`interval = 10`
- 缓存文件 mtime 严格按 10 秒节拍重写 —— **20 分钟限制被完全绕过**

**导入步骤**：FlClash → 配置 → 添加 → URL → 填 `http://127.0.0.1:18888/clash.yaml` → 确定 → 启用。
或直接点：`flclash://install-config?url=http://127.0.0.1:18888/clash.yaml`

> 前提：本机 watcher 进程在跑（见下方「本机运维」）。不在跑时本机源会连不上，
> 此时退回下面 GitHub 静态链接，但刷新会退回 5 分钟 / 20 分钟级别。

---

## 🌐 GitHub 静态链接（备用，不需要本机进程）

前缀 `https://raw.githubusercontent.com/VnchowWang/test/main/`

| 用途 | 路径 | 刷新 |
| --- | --- | --- |
| **推荐备用**：provider 版主配置 | `proxy-sub/clash-live-provider.yaml` | 内容每 5 分钟由 watcher 重写 |
| 完整版：9842 条 ACL4SSR 规则 + 39 组，节点内嵌 | `proxy-sub/clash-live.yaml` | 每 5 分钟整份重写 |
| 静态版：62 节点内嵌，ACL4SSR 全量规则（不自动更新） | `proxy-sub/clash.yaml` | 不更新 |
| v2rayN / NekoBox / Shadowrocket（base64） | `proxy-sub/live.txt` | 每 5 分钟重写 |
| 明文节点列表 / 测量元数据 | `proxy-sub/nodes.txt` · `proxy-sub/meta.json` | 每 5 分钟 |

GitHub raw 的 `max-age=300` 决定了这条通道的天花板是 5 分钟，再快也读不到新内容。

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
结论：**能用原生 Clash 配置就别过转换器**，转换一次节点就会从 62 掉到 59 左右。

---

## 🧭 节点命名与池子

命名格式：`机场｜🇸🇬国家NN｜NF+GPT+YT｜XXms`

- `机场` — 来源机场（渔云 CloudFisher / jisu / Stardream / 山水云 / 友连 / MuaCloud）
- `🇸🇬国家NN` — 出口落地国家与序号
- `NF+GPT+YT` — 实测解锁能力（Netflix / ChatGPT / YouTube）
- `XXms` — 发布时刻的实测延迟

**池子构成**：9 家机场订阅全量拉取（约 237 节点）→ 剔除 18 个「剩余流量/到期时间/官网」类信息伪节点
→ 全量拨号验证 → 存活约 146 → 按评分取前 80 进池 → 每轮发布 40 个最优。

**评分模型**：延迟（40%）+ 稳定性抖动（25%）+ 吞吐（20%）+ 解锁能力（15%），
已剔除出口 IP 与直连相同的假节点。

---

## 🛠 本机运维

```bash
# 看状态
curl -s --noproxy '*' http://127.0.0.1:18888/health
tail -20 "D:/Users/wangwenchao/Documents/deepseek-harness/default-workspace/work/watcher/watcher.log"

# 手动起（正常由计划任务自愈，不需手动）
schtasks //Run //TN ProxyLiveWatcher
```

- watcher 脚本：`work/watcher/proxy-live-watcher.cjs`
- 主配置生成：`work/watcher/mk-main.cjs`（改完跑 `node mk-main.cjs pub-main.yaml`）
- 自愈：计划任务 `ProxyLiveWatcher`（登录触发 + 每 5 分钟检查，单实例守卫防重复）
- 探测内核端口 `19440`(API) / `17940`(mixed)，本机源端口 `18888`
- 日志 `watcher.log`（快循环每 10 秒一行：`#N 活=X 隔离=Y 全池=Z`）

---

## ⚠️ 已知限制

1. **FlClash 无 `external-controller`**（FlClash 会把配置里的这个键强制清空），
   所以外部无法用 API 驱动 FlClash 的内核，切换只能靠内核自身的 `url-test`/`fallback`。
2. **Candytally / llG-New / LIME 三家订阅已失效**（403 / DNS 失败 / 非 YAML），池子里不含它们。
3. 端口 `18888` 被占用时 watcher 会在日志里报 `!! serve 端口错误`，本机源不可用，GitHub 静态链接不受影响。
4. 本机源只监听 `127.0.0.1`，**不对外网开放**，手机上用请走 GitHub 静态链接或自建反代。

---

_节点均为本机实测通过后发布；订阅内容含各机场节点凭证，仅个人使用。_

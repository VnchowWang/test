# 多机场优选订阅 · 实时版

> **节点状态每 10 秒重测一次，不可用立即切换；GitHub 上的订阅内容每 5 分钟自动重写**
> 全部节点在本机 mihomo 内核真实拨号验证，出口 IP 逐条核对，假节点已剔除

## 🥇 主订阅链接 —— 用这一条（FlClash / Mihomo / Clash Verge）

```
https://raw.githubusercontent.com/VnchowWang/test/main/proxy-sub/clash-live-provider.yaml
```

这条链接的是 **provider 架构**，导入一次以后再也不用手动更新：

| 谁在刷新 | 刷什么 | 频率 | 为什么这样 |
| --- | --- | --- | --- |
| 你客户端的内核 | 从 `live-provider.yaml` 重拉节点列表 | **30 秒** | `proxy-providers.live.interval: 30` |
| 你客户端的内核 | 对每个节点做健康检查 | **10 秒** | `health-check.interval: 10`, `lazy: false` |
| 你客户端的内核 | `⭐ 优选集` 重新挑最快节点 | **10 秒** | `interval: 10`, `tolerance: 0`（0 容差 = 慢一点就换） |
| 本机 watcher | 重写 GitHub 上的 `live-provider.yaml` | 5 分钟 | GitHub raw CDN `max-age=300`，比这更快也读不到新内容 |

**关键点：真正的 10 秒切换发生在你自己的内核里，不依赖 GitHub 也不依赖 FlClash 的更新定时器。**
即使 GitHub 挂了，只要 provider 缓存还在，内核照样每 10 秒重测并切换。

> FlClash 的订阅自动更新被硬编码为 **20 分钟**（`application.dart:119` `Timer(const Duration(minutes: 20), ...)`，且不看 `auto_update_duration_millis`）。所以**不要**用普通订阅链接指望它实时更新——必须用上面这条 provider 版：节点刷新由内核自己做（30s），FlClash 只管那份静态主配置。

### 三种订阅，按需选

| 用途 | 链接 |
| --- | --- |
| **推荐**：实时版，导入一次永久用 | `proxy-sub/clash-live-provider.yaml` |
| 完整版：9842 条 ACL4SSR 规则 + 39 组，节点内嵌（每 5 分钟整份重写） | `proxy-sub/clash-live.yaml` |
| 静态版：62 节点内嵌，ACL4SSR 全量规则（不自动更新） | `proxy-sub/clash.yaml` |
| v2rayN / NekoBox / Shadowrocket（base64，每 5 分钟重写） | `proxy-sub/live.txt` |
| 明文节点列表 / 测量元数据 | `proxy-sub/nodes.txt` · `proxy-sub/meta.json` |

完整 URL 前缀都是 `https://raw.githubusercontent.com/VnchowWang/test/main/`

### GitHub 直连慢？加速镜像

```
https://ghproxy.net/https://raw.githubusercontent.com/VnchowWang/test/main/proxy-sub/clash-live-provider.yaml
https://gh-proxy.com/https://raw.githubusercontent.com/VnchowWang/test/main/proxy-sub/clash-live-provider.yaml
```

> raw CDN 有 `Cache-Control: max-age=300`，任何镜像拿到的最新版本都不会比 5 分钟更新。

## 🔁 公开订阅转换（sub.v1.mk / api.v1.mk）

**转 Clash**
```
https://api.v1.mk/sub?target=clash&url=https%3A%2F%2Fgcore.jsdelivr.net%2Fgh%2FVnchowWang%2Ftest%40main%2Fproxy-sub%2Flive.txt
```

**转 mixed（v2rayN / NekoBox / Shadowrocket 通用）**
```
https://api.v1.mk/sub?target=mixed&url=https%3A%2F%2Fgcore.jsdelivr.net%2Fgh%2FVnchowWang%2Ftest%40main%2Fproxy-sub%2Flive.txt
```

### ⚠️ 转换器实测限制

| 问题 | 实测数据 | 应对 |
| --- | --- | --- |
| **源地址必须用 jsDelivr** | 本仓库的 `raw.githubusercontent.com` 源 **8/8 全被 403** 拒绝 | 上面链接已用 jsDelivr |
| **后端间歇 502** | 约 1/3 请求失败 | 多刷几次 |
| **clash target 会降级** | 15 次采样：10 次完整（~540KB）、5 次降级（~16KB，mihomo 读到 0 节点） | 看文件大小，>500KB 正常 |
| **只认 clash / mixed** | `target=sing-box`、`target=v2ray` 返回 `Invalid target!` | 改用 mixed |
| **篡改 xhttp 参数** | 星梦 xhttp 节点的 `path` 被清成 `/`，走转换链路连不上 | 用直连版 |

> **转换器只是给「连不上 GitHub」的客户端兜底，且只有约 2/3 概率拿到可用配置。**
> 想要稳定 + 实时，用 `clash-live-provider.yaml`。

## ⚙️ 实时是怎么做到的

```
本机 watcher（常驻 node 进程）
 ├─ 快循环 10s：探当前精选池 → 连续 2 次失败即摘除 → 隔离区抽样复活探测
 ├─ 慢循环 30min：重拉 9 家机场订阅 → 全量重测 238→~150 → 重建 40 节点池
 └─ 发布 5min 节流：Contents API 写 live-provider.yaml / clash-live.yaml / live.txt

GitHub（纯静态托管，不跑任何计算）
 └─ raw.githubusercontent.com 提供上面那些文件

你的客户端内核
 └─ 30s 重拉 provider 节点列表 + 10s 逐节点健康检查 + 10s 0 容差改选
```

**为什么计算不在 GitHub 上跑：** 这个 PAT 没有 `workflow` scope，`.github/workflows/*` 的写入被服务端拒绝（`403 Resource not accessible` / `refusing to allow a Personal Access Token to create or update workflow`），Pages 也是 403。所以 GitHub 只能当静态文件服务器，探测必须放在本地常驻进程。这反而更好——探测走本机真实网络，能测出从你这里出发的真实延迟。

**自愈：** Windows 计划任务 `ProxyLiveWatcher`，登录时启动 + **每 5 分钟唤醒一次**。watcher 活着时被单实例守卫（probe 端口占用）立即退出，死了就自动拉起。`MultipleInstancesPolicy=IgnoreNew`。

## 📊 当前池子

- **40 个节点**，来自 9 家机场订阅（CloudFisher / Candytally / llG / LIME / 极速 / 星梦 / 山水云 / 友连 / MUA）
- 其中 3 家已废：Candytally 403、llG 域名解析失败、LIME 返回非 YAML
- 每小时探测量：40 节点 × 6 次/分钟 ≈ 4 次/秒（不会触发探测风暴）

## 🧪 测速方法

1. **延迟** —— `/proxies/<name>/delay` 打 `http://www.gstatic.com/generate_204`，3 轮取中位数 + 抖动 + 丢包
2. **吞吐** —— 每节点独立 listener，**串行单流**下载 25MB（并发会让数字虚高 10 倍，实测 93MB/s vs 真实 12.5MB/s）
3. **出口归属** —— 每条连接单独查 `cloudflare.com/cdn-cgi/trace`，剔除出口与直连相同的假节点
4. **解锁** —— 分别打 OpenAI `/v1/models`、Netflix 剧集页、YouTube 播放页
5. **去重** —— 同出口 IP + 同端口 + 同协议只保留评分最高的一条

## 🏆 评分模型

```
总分 = 延迟分(40) + 吞吐分(35) + 稳定分(15) + 解锁分(10) + 协议分(5)
延迟: 60ms 满分，400ms 归零，对数插值
吞吐: 单流 60Mbps 满分，sqrt 曲线
稳定: 3 轮零丢包 + 抖动 < 50ms
解锁: GPT 4 分 + Netflix 4 分 + YouTube 2 分
协议: hysteria2 5 / anytls 4 / vless,trojan 3 / ss 2
```

## 📌 注意

- 节点来自个人机场订阅，**流量有限，请勿大范围传播**
- provider 模式下 `⭐ 优选集` 的第一个成员固定放当前最优节点——mihomo 在拿到首个探测结果前会先用第一个成员，放死的会短暂 502
- 订阅含节点凭证（UUID / 密码），拿到链接即可消耗流量配额

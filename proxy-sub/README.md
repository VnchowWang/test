# 多机场优选订阅

> **62 个可用节点** / 6 家机场 / 22 个地区
> 全部节点已在本机 mihomo 内核真实拨号验证，**62/62 在线**

生成时间：2026-11-02T06:34Z

## 🥇 主订阅链接（推荐）

**Clash / Mihomo / FlClash**
```
https://raw.githubusercontent.com/VnchowWang/test/main/proxy-sub/clash.yaml
```

已内置 **ACL4SSR 全量规则（9842 条）+ 39 个策略组**（OpenAI / Netflix / YouTube / Telegram / 游戏 / 广告拦截 / 直连 等），导入即用，不用再挂 rule-provider。

> ✅ `mihomo -t` 校验通过；内核实际加载后识别 **62 节点 + 33 策略组**；`mode: rule`、`mixed-port: 7890`。

### GitHub 直连慢？用这些加速镜像（都已实测返回同样的 574KB 完整文件）

```
https://ghproxy.net/https://raw.githubusercontent.com/VnchowWang/test/main/proxy-sub/clash.yaml
https://gh-proxy.com/https://raw.githubusercontent.com/VnchowWang/test/main/proxy-sub/clash.yaml
https://gcore.jsdelivr.net/gh/VnchowWang/test@main/proxy-sub/clash.yaml
```

> jsDelivr 的 `@main` 有缓存延迟（实测仍返回旧版 58KB）。要确保拿到最新版，用固定 commit 的写法：
> `https://gcore.jsdelivr.net/gh/VnchowWang/test@COMMIT_SHA/proxy-sub/clash.yaml`

**v2rayN / NekoBox / Shadowrocket / Sing-box（base64）**
```
https://raw.githubusercontent.com/VnchowWang/test/main/proxy-sub/base64.txt
```

| 内容 | 路径 |
| --- | --- |
| 明文节点列表 | `proxy-sub/nodes.txt` |
| 完整测量元数据 | `proxy-sub/meta.json` |

## 🔁 公开订阅转换（sub.v1.mk）

用 [sub.v1.mk](https://sub.v1.mk/) 的公共后端 `api.v1.mk`：

**转 Clash（带 ACL4SSR 规则）**
```
https://api.v1.mk/sub?target=clash&url=https%3A%2F%2Fgcore.jsdelivr.net%2Fgh%2FVnchowWang%2Ftest%40main%2Fproxy-sub%2Fbase64.txt
```

**转 mixed（v2rayN / NekoBox / Shadowrocket 通用，62 节点全在，但无分组无规则）**
```
https://api.v1.mk/sub?target=mixed&url=https%3A%2F%2Fgcore.jsdelivr.net%2Fgh%2FVnchowWang%2Ftest%40main%2Fproxy-sub%2Fbase64.txt
```

### ⚠️ 转换器实测限制（已踩过的坑）

| 问题 | 实测数据 | 应对 |
| --- | --- | --- |
| **源地址必须用 jsDelivr** | 本仓库的 `raw.githubusercontent.com` 源 **8/8 全被 403 Forbidden** 拒绝 | 上面链接已用 jsDelivr 源 |
| **后端间歇 502** | `error code: 502`，约 1/3 请求失败 | 多刷几次 |
| **clash target 会降级** | 15 次采样：**10 次完整**（~540KB，62 节点 + 10 组 + 9804 规则）、**5 次降级**（~16KB，旧字段名 `Proxy:`，mihomo 读到 **0 节点**） | **看文件大小**：>500KB 正常，~16KB 就重拉 |
| **只认 clash / mixed** | `target=sing-box`、`target=v2ray` 返回 `Invalid target!` | 改用 mixed |
| **篡改 xhttp 参数** | 星梦 xhttp 节点 `path` 从 `/f6d93c8849ba0bc057138ccd` 被清成 `/`，该节点走转换链路连不上 | 需要星梦节点就用直连 `clash.yaml` |

> **结论：追求稳定请直接用 `clash.yaml`（62/62 全通、零篡改、规则完整）。**
> 转换器只是给「不方便直连 GitHub」的客户端兜底，且只有约 2/3 概率拿到可用配置。

## 📊 机场分布

| 机场 | 节点数 |
| --- | --- |
| 友连 | 32 |
| 山水云 | 15 |
| 星梦 | 6 |
| 渔云 | 4 |
| 极速 | 4 |
| MUA | 1 |

## 🌏 地区分布

TW 11 · US 10 · JP 9 · HK 8 · SG 6 · TR 2 · EG / TH / KR / IN / NL / NZ / CL / PL / MX / CH / PH / DE / GB / FR / ES / IE 各 1

## 🔓 解锁能力

| 服务 | 可用节点 |
| --- | --- |
| 🤖 ChatGPT / OpenAI | **56** |
| 📺 YouTube | **56** |
| 🎬 Netflix | **7** |

## 🧪 测速方法

全部节点在本地 mihomo 内核中真实拨号：

1. **延迟** —— `/proxies/<name>/delay` 打 `http://www.gstatic.com/generate_204`，3 轮取中位数 + 抖动 + 丢包
2. **吞吐** —— 每节点独立 listener，**串行单流**下载 25MB（并发会让数字虚高 10 倍）
3. **出口归属** —— 每条连接单独查 `cloudflare.com/cdn-cgi/trace`，确认国家/城市，剔除出口与直连相同的假节点
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
- 机场节点会变动，失效属正常，可重新跑一遍生成
- 订阅中含节点凭证（UUID / 密码），**拿到本链接即可消耗你的流量配额**

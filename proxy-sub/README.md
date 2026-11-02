# 多机场优选订阅

> 本地实测择优生成，覆盖 **62 个可用节点** / 6 家机场 / 22 个地区
> 全部节点在本机 mihomo 内核中真实拨号验证，**62/62 全部在线**

**生成时间**: 2026-11-02T06:15Z

## 订阅链接（直连，推荐）

| 用途 | 链接 |
| --- | --- |
| **Clash / Mihomo / FlClash** | `https://raw.githubusercontent.com/VnchowWang/test/main/proxy-sub/clash.yaml` |
| Clash 国内加速（jsDelivr） | `https://gcore.jsdelivr.net/gh/VnchowWang/test@main/proxy-sub/clash.yaml` |
| v2rayN / NekoBox / Sing-box（base64） | `https://raw.githubusercontent.com/VnchowWang/test/main/proxy-sub/base64.txt` |
| 明文节点列表 | `https://raw.githubusercontent.com/VnchowWang/test/main/proxy-sub/nodes.txt` |
| 完整测量元数据 | `https://raw.githubusercontent.com/VnchowWang/test/main/proxy-sub/meta.json` |

`clash.yaml` 已内置 **ACL4SSR 全量规则**（9842 条）+ 39 个策略组（OpenAI / Netflix / YouTube / Telegram / 游戏 / 直连 等），导入即用，无需再叠加 rule-provider。

## 公开订阅转换（可选）

用 [sub.v1.mk](https://sub.v1.mk/) 的公共后端把 base64 转成其他格式：

**Clash（含 ACL4SSR 规则）**
```
https://api.v1.mk/sub?target=clash&url=https%3A%2F%2Fraw.githubusercontent.com%2FVnchowWang%2Ftest%2Fmain%2Fproxy-sub%2Fbase64.txt
```

**混合格式（v2rayN / NekoBox / Shadowrocket 通用）**
```
https://api.v1.mk/sub?target=mixed&url=https%3A%2F%2Fraw.githubusercontent.com%2FVnchowWang%2Ftest%2Fmain%2Fproxy-sub%2Fbase64.txt
```

国内网络访问转换器时，可把 `url=` 的参数换成 jsDelivr 源：

```
https://api.v1.mk/sub?target=clash&url=https%3A%2F%2Fgcore.jsdelivr.net%2Fgh%2FVnchowWang%2Ftest%40main%2Fproxy-sub%2Fbase64.txt
```

> ⚠️ 转换器说明
> - `api.v1.mk` 只支持 `target=clash` 与 `target=mixed`；`sing-box` / `v2ray` 会返回 `Invalid target!`。
> - 该后端是**免费公共实例，会间歇性 502**（实测约 1/3 成功率），失败重试即可。
> - 转换器会**篡改部分节点参数**：星梦机场 xhttp 节点的 `path` 会被清成 `/`，导致该节点走转换链路时不可用。**要求最高可用性请直接用上面的 `clash.yaml` 直连链接**（62/62 全通）。

## 机场分布

| 机场 | 节点数 |
| --- | --- |
| 友连 | 32 |
| 山水云 | 15 |
| 星梦 | 6 |
| 渔云 | 4 |
| 极速 | 4 |
| MUA | 1 |

## 地区分布

TW 11 · US 10 · JP 9 · HK 8 · SG 6 · TR 2 · EG/TH/KR/IN/NL/NZ/CL/PL/MX/CH/PH/DE/GB/FR/ES/IE 各 1

## 解锁能力

| 服务 | 可用节点 |
| --- | --- |
| 🤖 ChatGPT / OpenAI | **56** |
| 📺 YouTube | **56** |
| 🎬 Netflix | **7** |

## 测速方法

全部节点在本地 mihomo 内核中真实拨号：

1. **延迟** —— `/proxies/<name>/delay` 打 `http://www.gstatic.com/generate_204`，3 轮取中位数 + 抖动 + 丢包
2. **吞吐** —— 每节点独立 listener，**串行单流**下载 25MB（并发会让数字虚高 10 倍）
3. **出口归属** —— 每条连接单独查 `cloudflare.com/cdn-cgi/trace`，确认国家/城市，剔除出口与直连相同的假节点
4. **解锁** —— 分别打 OpenAI `/v1/models`、Netflix 剧集页、YouTube 播放页
5. **去重** —— 同出口 IP + 同端口 + 同协议只保留评分最高的一条

## 评分模型

```
总分 = 延迟分(40) + 吞吐分(35) + 稳定分(15) + 解锁分(10) + 协议分(5)
延迟: 60ms 满分，400ms 归零，对数插值
吞吐: 单流 60Mbps 满分，sqrt 曲线
稳定: 3 轮零丢包 + 抖动 < 50ms
解锁: GPT 4 分 + Netflix 4 分 + YouTube 2 分
协议: hysteria2 5 / anytls 4 / vless,trojan 3 / ss 2
```

## 注意

- 节点来自个人机场订阅，**流量有限**，请勿大范围传播
- 机场节点会变动，失效属正常，可重新跑一遍生成
- 订阅中含节点凭证（UUID / 密码），**知道本链接即可使用你的流量配额**

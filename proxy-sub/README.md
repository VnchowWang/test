# 多机场优选订阅

> **62 个可用节点** / 6 家机场 / 22 个地区
> 全部节点已在本机 mihomo 内核真实拨号验证，**62/62 在线**

生成时间：2026-11-02T06:20Z

## 🥇 主订阅链接（推荐直接用这个）

**Clash / Mihomo / FlClash**
```
https://raw.githubusercontent.com/VnchowWang/test/main/proxy-sub/clash.yaml
```

国内直连 GitHub 慢时，用 jsDelivr 加速：
```
https://gcore.jsdelivr.net/gh/VnchowWang/test@main/proxy-sub/clash.yaml
```

这个文件已内置 **ACL4SSR 全量规则（9842 条）+ 39 个策略组**（OpenAI / Netflix / YouTube / Telegram / 游戏 / 广告拦截 / 直连 等），导入即用，不用再挂 rule-provider。

**v2rayN / NekoBox / Shadowrocket / Sing-box（base64）**
```
https://raw.githubusercontent.com/VnchowWang/test/main/proxy-sub/base64.txt
```

**其他文件**

| 内容 | 链接后缀 |
| --- | --- |
| 明文节点列表 | `/proxy-sub/nodes.txt` |
| 完整测量元数据 | `/proxy-sub/meta.json` |

## 🔁 公开订阅转换（sub.v1.mk）

用 [sub.v1.mk](https://sub.v1.mk/) 的公共后端 `api.v1.mk` 转成别的格式：

**转 Clash（保留 ACL4SSR 规则）**
```
https://api.v1.mk/sub?target=clash&url=https%3A%2F%2Fgcore.jsdelivr.net%2Fgh%2FVnchowWang%2Ftest%40main%2Fproxy-sub%2Fbase64.txt
```

**转 mixed（v2rayN / NekoBox / Shadowrocket 通用）**
```
https://api.v1.mk/sub?target=mixed&url=https%3A%2F%2Fgcore.jsdelivr.net%2Fgh%2FVnchowWang%2Ftest%40main%2Fproxy-sub%2Fbase64.txt
```

### ⚠️ 转换器的实测限制（已踩过的坑，务必先读）

1. **源地址必须用 jsDelivr，不能用 raw.githubusercontent**
   该后端的 nginx 会直接对本仓库的 raw 地址返回 `403 Forbidden`（实测 8/8 全拒）。上面给的链接已用 jsDelivr 源。

2. **后端是免费公共实例，会间歇性 `502 error code`**
   实测约 1/3 的请求 502，**多刷几次/重试即可**。

3. **只支持 `target=clash` 和 `target=mixed`**
   `target=sing-box` / `target=v2ray` 会返回 `Invalid target!`。

4. **转换器会篡改部分节点参数**
   星梦机场的 xhttp 节点，其 `path`（`/f6d93c8849ba0bc057138ccd`）会被清成 `/`，导致这类节点走转换链路时连不上。

5. **偶发降级输出**
   约 1/12 的请求会返回只有 `Proxy:` 段、缺策略组和规则的残缺配置（约 16KB，正常应为 ~540KB）。**看到文件特别小就重新拉一次。**

> 结论：**追求稳定请直接用上面的 `clash.yaml` 直连链接（62/62 全通，无篡改）。** 转换器是给不方便直连 GitHub 的客户端兜底用的。

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

# 多机场优选订阅

> 本地实测择优生成，覆盖 62 个可用节点 / 6 家机场 / 22 个地区

**生成时间**: 2026-11-02T05:54:57.662Z

## 订阅链接

| 用途 | 链接 |
| --- | --- |
| Clash / Mihomo / FlClash | `https://raw.githubusercontent.com/VnchowWang/test/main/proxy-sub/clash.yaml` |
| Clash 国内加速（jsDelivr） | `https://cdn.jsdelivr.net/gh/VnchowWang/test@main/proxy-sub/clash.yaml` |
| v2rayN / NekoBox / Sing-box（base64） | `https://raw.githubusercontent.com/VnchowWang/test/main/proxy-sub/base64.txt` |
| 明文节点列表 | `https://raw.githubusercontent.com/VnchowWang/test/main/proxy-sub/nodes.txt` |
| 完整测量元数据 | `https://raw.githubusercontent.com/VnchowWang/test/main/proxy-sub/meta.json` |

## 机场分布

- **山水云**: 15 节点
- **星梦**: 6 节点
- **友连**: 32 节点
- **渔云**: 4 节点
- **极速**: 4 节点
- **MUA**: 1 节点

## 地区分布

- TW: 11
- US: 10
- JP: 9
- HK: 8
- SG: 6
- TR: 2
- EG: 1
- TH: 1
- KR: 1
- IN: 1
- NL: 1
- NZ: 1
- CL: 1
- PL: 1
- MX: 1
- CH: 1
- PH: 1
- DE: 1
- GB: 1
- FR: 1
- ES: 1
- IE: 1

## 解锁能力

- 🤖 ChatGPT / OpenAI: **56** 节点可用
- 🎬 Netflix: **7** 节点解锁
- 📺 YouTube: **56** 节点直连可用

## 测速方法

全部节点在本地 mihomo 内核中真实拨号：

1. **延迟**：`/proxies/<name>/delay` 打 `http://www.gstatic.com/generate_204`，3 轮取中位数 + 抖动 + 丢包
2. **吞吐**：每节点独立 listener，**串行单流**下载 25MB（并发会让数字虚高 10 倍）
3. **出口归属**：每条连接单独查 `cloudflare.com/cdn-cgi/trace`，确认国家/城市，剔除出口与直连相同的假节点
4. **解锁**：分别打 OpenAI `/v1/models`、Netflix 剧集页、YouTube 播放页
5. **去重**：同出口 IP + 同端口 + 同协议只保留评分最高的一条

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

# 两轮优选节点自动订阅与服务分流

从9份原始 Clash / Mihomo YAML 订阅精确选取 **35个节点**，每30分钟更新。完整订阅包含Netflix、Disney+、OpenAI、Claude等服务分流组，可直接导入FlClash。

## 节点顺序与分组

全部节点放在同一个总选择组中：**第一轮27条在上，第二轮8条在下**。自动测速、故障转移和各服务组中的节点列表也保持这个顺序。

总选择组为兼容已有选择记录，保留名称 **9929 手动选择**；另外保留 **9929 自动测速**、**9929 故障转移**。第二轮包含普通公网和中转节点，35条并不都代表9929线路。显示名保持`来源 :: 原始节点名`，协议字段与服务器地址从原订阅同步。

第二轮按下列顺序追加（第28—35条）：

1. AoYo-Cloud：韩国M区-上港AWS①
2. AoYo-Cloud：大板B区-上港AWS①
3. 追云加速(1)：香港03【vip3】[H]
4. 追云加速：日本01【vip2 】[H]
5. AoYo-Cloud：香港C区-上港YC①
6. 掌中世界(1)：HK07🇭🇰办公日常
7. Stardream：直连 台湾 07 | 0.5x
8. 色色小站：HK | ANYTLS

此处采用第二轮表格中的8条日常推荐；没有将高倍率20X备用节点或其他未列入日常表格的候选自动加入。

## 服务分流

| 选择组 | 分流范围 |
| --- | --- |
| Netflix | Netflix主站、接口、图片、视频和Fast测速 |
| Disney+ | Disney+站点、账号、已确认的Disney租户接口与播放域名 |
| OpenAI | ChatGPT、OpenAI API、登录、素材、Sora与已确认的租户CDN |
| Claude | Claude/Anthropic API、登录、附件、Artifacts与组件域名 |
| YouTube | YouTube、视频、图片与指定Google API主机 |
| Telegram | Telegram域名及已核对的原生客户端DC地址段 |
| Apple | Apple、iCloud与相关资源域名 |
| Microsoft | Microsoft、Office、OneDrive及登录域名 |

每个服务组**默认跟随总选择组**，也可单独选择35条中的任意节点。分流规则优先于国内直连和最终兜底规则。局域网与私网直连，GeoIP识别为中国的其他流量直连，其余流量跟随总选择组。

完整配置包含fake-IP DNS与HTTP/TLS/QUIC嗅探，以便匹配域名；不设置客户端TUN开关。请使用FlClash的**规则模式**。客户端若启用覆盖订阅DNS、分组或规则的覆写，应检查实际生效配置。

这些分组用于选择出站线路，不代表每个节点已通过Netflix、Disney+、OpenAI或Claude解锁验证；服务可用性还受出口地区、账户及服务端策略影响。域名规则覆盖经审阅的服务命名空间，不将整个AWS、Auth0、Cloudflare或其他共享云厂商归入单个服务。

规则参考：[OpenAI网络要求](https://help.openai.com/en/articles/9247338-network-recommendations-for-chatgpt-errors-on-web-and-apps)、[Claude网络要求](https://code.claude.com/docs/en/network-config.md)、[MetaCubeX服务域名清单](https://github.com/MetaCubeX/meta-rules-dat/tree/meta/geo/geosite)及[Telegram地址清单](https://github.com/MetaCubeX/meta-rules-dat/blob/meta/geo/geoip/telegram.list)。服务规则为随代码发布的审阅清单，不会因为节点名称含Netflix或AI就推断解锁能力。

## 更新与固定链接

工作流位于[update-subscription.yml](.github/workflows/update-subscription.yml)，cron为`17,47 * * * *`，即北京时间每小时17分和47分，支持手动运行。GitHub可能延迟调度；客户端需要刷新订阅才能加载新版。

保留现有Gist和文件名，原固定订阅URL继续有效：

- `9929-flclash.yaml`：**完整版**，包含35条节点、所有分组、DNS与分流规则；想使用服务分流请选择这个链接。
- `9929-proxies.yaml`：只有35条节点，供已有配置合并，**不包含服务组和规则**。

文件名中的9929是沿用历史链接；真实链接仅私下提供，不放入公开仓库。公开仓库只含程序、精确节点身份、测试、说明和净化状态。带密码的配置在原有secret/unlisted Gist中；持有链接或Gist ID的人可以读取配置及历史，因此它不等于需要登录的私有存储。

## 原订阅来源

| 来源 | 数量 | GitHub Actions Secret |
| --- | ---: | --- |
| 掌中世界(1) | 15（第一轮14、第二轮1） | `SOURCE_ZHANGZHONG` |
| Speedy | 8 | `SOURCE_SPEEDY` |
| Muacloud网络加速.yaml | 3 | `SOURCE_MUACLOUD` |
| 星河 583 | 2 | `SOURCE_XINGHE` |
| AoYo-Cloud | 3 | `SOURCE_AOYO` |
| 追云加速(1) | 1 | `SOURCE_ZHUIYUN_VIP3` |
| 追云加速 | 1 | `SOURCE_ZHUIYUN_VIP2` |
| Stardream | 1 | `SOURCE_STARDREAM` |
| 色色小站 | 1 | `SOURCE_SESE` |
| 合计 | **35** | |

[selectors.json](selectors.json)的`sources`控制精确选取身份，`node_order`控制跨来源的全局顺序，因此同属掌中世界的第二轮HK07也会排在原27条之后。程序保留协议选项及最新服务器，不固定为测量时的IP。

任一来源请求失败、节点缺失、同名歧义或参数无效时，**不替换上次完整订阅**；只有35/35全部匹配才发布。两份配置和净化状态在同一次Gist请求中更新。自动同步不重新测量路由、速度或解锁情况，也不按地区近似替换改名节点。

## 运行与部署

Python 3.12+，依赖见[requirements.txt](requirements.txt)。

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python subscription_bundle.py build
```

本地构建需通过环境变量注入上表9个原订阅URL。发布还需`GIST_TOKEN`和原有`GIST_ID`，执行`python subscription_bundle.py publish`。原订阅仅在受信进程中使用，不写入代码、命令行或公共日志，也不发送给第三方订阅转换器。

GitHub工作流使用只读`GITHUB_TOKEN`；发布步骤单独接收9个来源Secret、`GIST_TOKEN`与`GIST_ID`。Gist令牌需要账户级Gists写权限，工作流修改需要相应仓库权限。只上传净化的更新状态产物，不上传含凭据的配置或固定链接文件。

[工作流运行记录](https://github.com/VnchowWang/test/actions/workflows/update-subscription.yml)与[部署验证记录](route-audit/2026-11-05/subscription-live-refresh-status.json)可用于核对实际匹配数和最近验证。已有其他目录与历史报告保留。离线测试涵盖精确选取、协议保留、全局排序、规则优先级、租户域名边界、Telegram地址、失败保留与Gist发布边界；实际发布以后续线上运行及固定URL核验为准。

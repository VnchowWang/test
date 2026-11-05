# 27 个已测 AS9929 节点自动订阅

从四份原始 Clash / Mihomo YAML 订阅中，按「来源名 + 原始节点名」精确选取 27 个节点。Python + PyYAML 每次重新读取原订阅，保留节点协议配置与最新服务器信息，生成可直接导入 FlClash 的完整配置，以及仅含 `proxies` 的合集。

目标代码仓库：<https://github.com/VnchowWang/test>（公开）。**公开仓库只保存程序、精确 selector、测试和文档；带密码的输出设计为发布到 secret gist。**

**部署状态（2026-11-05）**：四个原订阅 Secret、`GIST_TOKEN` 和 `GIST_ID` 已配置；实际工作流已安装到 [`.github/workflows/update-subscription.yml`](.github/workflows/update-subscription.yml)，每六小时更新，并支持手动运行。本机重新抓取四家原订阅，完整匹配27/27；两个固定订阅URL均返回HTTP 200，完整配置通过Mihomo校验。[首次线上运行](https://github.com/VnchowWang/test/actions/runs/42054467635)已成功，四家原订阅完整匹配27/27并发布；随后再次读取两个固定URL，均确认与这次线上发布一致。[工作流运行记录](https://github.com/VnchowWang/test/actions/workflows/update-subscription.yml)和[部署验证记录](route-audit/2026-11-05/subscription-live-refresh-status.json)可用于后续核对。真实订阅URL不写入公开仓库。

自动更新必须从全部四份原订阅完整找到这27个精确身份；任一来源失败时，保留上一次完整订阅。

## 选择范围

| 来源 | 数量 | Actions Secret（原订阅 URL） |
| --- | ---: | --- |
| 掌中世界(1) | 14 | `SOURCE_ZHANGZHONG` |
| Speedy | 8 | `SOURCE_SPEEDY` |
| Muacloud网络加速.yaml | 3 | `SOURCE_MUACLOUD` |
| 星河 583 | 2 | `SOURCE_XINGHE` |
| 合计 | **27** | |

原需求提到三家，但要求保留的 27 个已测节点实际横跨四家，所以保留四家。`selectors.json` 只含来源名、环境变量名和精确原始节点名，无服务器、入口 IP、端口、密码或订阅 URL。CSV 中 EMO 的证据是 `AS10099 only, AS9929 not observed`，不在这 27 个节点中，不能只用字面包含 `AS9929` 判断。

这份选择反映历史网络实测结果。自动更新只同步这些身份的配置；**不会重新验证更新后的线路仍经过 AS9929，也不会自动扩大候选集**。线路变更需要另行复测。

## 输出与失败策略

所有输出默认写入被 Git 忽略的 `.private/`：

- `9929-flclash.yaml`：完整 FlClash / Mihomo 配置，含手动选择、URL-test 自动测速、fallback 故障转移和 `MATCH` 规则；监听本机混合端口 7890，禁止 LAN 连接。
- `9929-proxies.yaml`：仅含 `proxies:`，供已有配置使用 provider / 合并工具导入，不能代替完整客户端配置。
- `update-status.json`：仅含时间、来源名、匹配计数、缺失/重名/无效节点名、固定错误代码与发布状态；不含订阅 URL、服务器或密码。
- `subscription-links.json`：首次创建或更新 gist 后写入固定的完整配置 URL、proxies URL 和 gist ID。**这个文件也应保密。**

每次必须完整找到 27 个精确身份，才生成新的配置并允许发布。节点改名、重复同名、单个来源请求失败、缺少 Secret、订阅 YAML 无效或节点基本参数无效，都会返回非零退出码，写出状态，并保留原有本地配置和 gist。没有按服务器/IP近似匹配、挑同地区替代节点或清空输出的回退行为。

显示名使用 `来源 :: 原始节点名` 以避免跨来源重名。所有其他协议字段会递归保留，包括密码、UUID、TLS / Reality / WS 参数、UDP 和未来扩展字段。若节点的 `dialer-proxy` 引用了本次同来源选中的节点，引用同步改为新显示名；引用未选中节点/分组则阻止发布，避免生成不完整依赖。

所有来源通过 HTTPS 获取，拒绝降级 HTTP 重定向；只支持含 `proxies` 列表的 Clash YAML。若原 URL 返回 Base64 URI 列表，请由订阅提供方给出 Clash / Mihomo 格式 URL。不会向第三方订阅转换服务发送私密 URL。

## 为什么使用 secret gist

公开仓库的 raw 文件、Release 和 Actions 配置附件会公开节点密码。这里用独立 `GIST_TOKEN` 更新 **secret（unlisted）gist**，每次把两份配置和状态放入同一个 API PATCH 请求。程序在修改已有 gist 前检查 `public == false`，拒绝向公开 gist 发布。

**Secret gist 不是有登录鉴权的私有存储。任何拿到 raw 链接或 gist ID 的人都能读取节点凭据；其他文件和历史修订也可经该 gist 访问。** 不要把链接粘贴到公开 issue、日志、截图、README 或聊天群。泄露时仅删当前文件不能撤销历史密码，应撤销上游订阅凭据，并删除/替换 gist。若需要每次访问都鉴权，须改用客户端支持的鉴权服务或自己控制的 HTTPS 网关；这不在本实现的默认部署中。

导入链接使用**不带 revision 的 URL**，例如（占位示例，不能直接导入）：

```text
https://gist.githubusercontent.com/OWNER/GIST_ID/raw/9929-flclash.yaml
```

真实链接仅写入本地 `.private/subscription-links.json`，不会出现在 Actions 日志或产物中。保持同一个 `GIST_ID` 和文件名，客户端刷新这个 URL 就能取得最新配置。GitHub CDN 或客户端缓存可能带来短暂延迟；只有定时更新运行成功后才有新版本。

## 本地运行与首次创建 gist

需要 Python 3.12+。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

由本地可信流程给当前进程注入上表四个 `SOURCE_*` 环境变量，**不要把真实值写在命令行、代码、提交文件或公共日志中**。本项目不读取原始客户端配置或数据库，运行凭据由操作者提供。

先仅在本地构建验证：

```powershell
.\.venv\Scripts\python.exe subscription_bundle.py build
```

首次创建需另外注入 `GIST_TOKEN`，且不设置 `GIST_ID`。令牌可使用具有账户级 **Gists: Write** 权限的细粒度 PAT，或具有 `gist` 作用域的 classic PAT；默认 `GITHUB_TOKEN` 不能代替这个令牌。执行：

```powershell
.\.venv\Scripts\python.exe subscription_bundle.py init-gist
```

程序明确请求 `public: false`。成功后，在本地打开 `.private/subscription-links.json`，把 `flclash_url` 复制到 FlClash 的「从 URL 导入」；`proxies_url` 留给仅需 provider 的配置。读取该文件时注意不要把内容发到公共输出。把其中 `gist_id` 存入仓库 Secret `GIST_ID`。

`init-gist` 不应放进定时任务；重复执行可能产生额外 gist。如果发送创建请求后网络中断，GitHub 可能已经创建成功，应先在自己账号的 gist 页面检查，再决定是否重试。

后续本地更新（注入全部六个环境变量后）：

```powershell
.\.venv\Scripts\python.exe subscription_bundle.py publish
```

正常更新要求已有 `GIST_ID`，不会因 Secret 遗漏意外创建另一份 gist。发布请求之后发生网络中断时，状态的 `publication_outcome` 为 `unknown`、`retained_previous` 为 `null`：服务器可能保留旧版或已经接收完整新版，不能声称远端一定没改变。确认响应成功后为 `confirmed`。源数据验证失败时完全不会调用 gist API。

## GitHub Actions 部署

部署需要仓库级 **Contents: Read and write、Workflows: Write、Secrets: Read and write、Actions: Read and write**，以及账户级 **Gists: Write**。现有细粒度令牌已通过 Secrets 写入、工作流上传和 secret gist 创建验证；凭据保留在 GitHub CLI 登录及仓库 Secrets 中，未写入公开代码。

部署前先使用有效访问方式检查目标仓库当前结构，再把以下文件合并进去：`subscription_bundle.py`、`selectors.json`、`requirements.txt`、`tests/test_subscription_bundle.py`、`.github/workflows/update-subscription.yml`，以及适合合并的 README / `.gitignore`。不要直接覆盖已有同名文件。只暂存这些已审阅的源文件；不要暂存 `.private/`、`.deps/`、`.pip-cache/` 或任何真实节点输出。

在仓库 **Settings → Secrets and variables → Actions → Repository secrets** 设置：

| Secret | 内容 |
| --- | --- |
| `SOURCE_ZHANGZHONG` | 掌中世界(1) 原始 Clash YAML 订阅 URL |
| `SOURCE_SPEEDY` | Speedy 原始 Clash YAML 订阅 URL |
| `SOURCE_MUACLOUD` | Muacloud 原始 Clash YAML 订阅 URL |
| `SOURCE_XINGHE` | 星河 583 原始 Clash YAML 订阅 URL |
| `GIST_TOKEN` | 具有账户级 `Gists: Write` 权限的细粒度PAT，或具有 `gist` 作用域的令牌 |
| `GIST_ID` | 已创建的 secret gist ID |

Actions 每六小时第 17 分钟（UTC）执行一次，并支持 **Actions → Update selected 9929 subscription → Run workflow** 手动触发。仓库权限只有 `contents: read`；不执行 git commit / push。所有 Actions 均固定到具体提交 SHA；源 URL 和 gist 令牌仅注入最后的发布步骤，离线测试没有 Secrets。并发更新串行，避免同一工作流互相覆盖。

公开 Actions 日志仅输出匹配计数/结果。唯一上传产物是已净化的 `update-status.json`（保留七天），不上传配置、完整私密目录或链接。工作流因丢失节点而失败时，在状态产物查看 `sources[].missing`、`ambiguous`、`invalid` 或 `errors`。核实改名或线路变化后，再审阅并修改 selector；不要为了让任务变绿而替换成别的节点。

公开仓库的定时 Actions 可能受 GitHub 的无活动暂停策略影响。即使采用定时任务，也建议在 FlClash 设置合理的订阅刷新周期，并定期查看最新成功时间。可信贡献者能修改工作流并接触 Secrets，仓库写权限也应妥善管理。

## 验证与线路报告

已通过27项离线测试，另由独立Mihomo核心完成27条节点体验复测：每节点6次HTTPS探测和2次1MiB下载。测试结果见[体验报告](route-audit/2026-11-05/quality/report.md)及[完整排名](route-audit/2026-11-05/quality/ranking.csv)。本次优先试用掌中世界HK02、SG01 AI优化、台湾01 AI专线；合集仍保留全部27条，客户端可手动切换或自动测速。

公开代码部署保留已有的 `proxy-sub/` 和 `sub/`。自动抓取能否成功以最近一次状态为准；GitHub定时任务不等于实时推送。

测试使用纯虚构节点和模拟网络请求，覆盖全部 27 个身份与四来源计数、协议字段/新服务器保留、改名缺失、同名歧义、跨来源同名、来源失败脱敏、YAML 安全解析、下载大小限制、HTTPS、完整 FlClash 分组、公开 gist 拒绝发布、原子 gist 请求、固定订阅链接、首次创建、上次有效版本保留和 CLI 错误边界。真实来源同步和线上 gist 发布需要操作者注入有效 Secrets 后另行验证。

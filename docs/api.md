# QinglongScripts 项目 API 文档

> 汇总项目中所有脚本调用的 API 接口，按服务分类整理。

---

## 目录

- [一、百度贴吧 (Tieba.py)](#一百度贴吧-tiebapy)
- [二、阿里云盘 (Aliyun.py)](#二阿里云盘-aliyunpy)
- [三、Bilibili (Bilibili.py)](#三bilibili-bilibilipy)
- [四、森空岛 (skyland.py)](#四森空岛-skylandpy)
- [五、NodeSeek (Nodeseek.py)](#五nodeseek-nodeseekpy)
- [六、HelloGitHub (HelloGithub.py)](#六hellogithub-hellogithubpy)
- [七、机场服务 (Airport.py)](#七机场服务-airportpy)
- [八、Bitwarden 备份 (Sync_Password.py)](#八bitwarden-备份-sync_passwordpy)
- [九、SSL 证书检查 (SSL.py)](#九ssl-证书检查-sslpy)
- [十、Telegram Bot API (通用)](#十telegram-bot-api-通用)
- [十一、掌上无畏契约 (ValorantStore.py)](valorant-api.md)

---

## 一、百度贴吧 (Tieba.py)

> 每日自动签到，获取关注的贴吧列表并对每个贴吧签到。

### 1.1 PC Web 端 API（来源：HAR 抓包）

#### 获取配置/实验数据

```
GET https://tieba.baidu.com/mo/q/getConfigData
```

| 参数 | 说明 |
|------|------|
| `amis_key` | 配置 key |
| `subapp_type` | 固定 `pc` |
| `_client_type` | 固定 `20` |
| `sign` | MD5 签名 |

---

#### 获取个性化推荐内容

```
GET https://tieba.baidu.com/c/f/excellent/personalized_pc
```

| 参数 | 说明 |
|------|------|
| `load_type` | 加载类型，首页固定 `1` |
| `subapp_type` | 固定 `pc` |
| `_client_type` | 固定 `20` |
| `sign` | MD5 签名 |

---

#### 获取左侧边栏 — 关注的贴吧列表 (PC)

```
GET https://tieba.baidu.com/c/f/pc/homeSidebarLeft
```

| 参数 | 必填 | 说明 |
|------|------|------|
| `pn` | 否 | 页码，默认 1 |
| `list_type` | 否 | 列表类型，`like` 为关注的贴吧 |
| `subapp_type` | 是 | 固定 `pc` |
| `_client_type` | 是 | 固定 `20` |
| `sign` | 是 | MD5 签名 |

---

#### 获取右侧边栏

```
GET https://tieba.baidu.com/c/f/pc/homeSidebarRight
```

| 参数 | 说明 |
|------|------|
| `subapp_type` | 固定 `pc` |
| `_client_type` | 固定 `20` |
| `sign` | MD5 签名 |

---

#### 同步/心跳

```
GET https://tieba.baidu.com/c/s/pc/sync
```

| 参数 | 说明 |
|------|------|
| `subapp_type` | 固定 `pc` |
| `_client_type` | 固定 `20` |
| `sign` | MD5 签名 |

---

### 1.2 Mobile/WAP API（脚本实际使用）

#### 获取 TBS / 验证登录

```
GET http://tieba.baidu.com/dc/common/tbs
```

响应字段：`is_login`、`tbs`

---

#### 获取用户信息

```
GET https://tieba.baidu.com/f/user/json_userinfo
```

响应：`data.show_nickname`

---

#### 获取关注的贴吧列表（含等级）

```
POST http://c.tieba.baidu.com/c/f/forum/like
```

| Body 参数 | 说明 |
|-----------|------|
| `BDUSS` | 登录凭证 |
| `_client_type` | 固定 `2` |
| `_client_id` | 固定 `wappc_1534235498291_488` |
| `_client_version` | 固定 `9.7.8.0` |
| `_phone_imei` | 固定 `000000000000000` |
| `page_no` | 页码 |
| `page_size` | 每页数量，固定 `200` |
| `sign` | MD5 签名（密钥 `tiebaclient!!!`） |

响应字段：

| 字段 | 说明 |
|------|------|
| `forum_list.non-gconforum` | 今日未签到贴吧列表 |
| `forum_list.gconforum` | 今日已签到贴吧列表 |
| `level_id` | 用户在该吧的等级 |
| `cur_score` | 当前经验值 |
| `levelup_score` | 升级所需经验值 |
| `has_more` | 是否还有更多页 |

---

#### 贴吧签到

```
POST http://c.tieba.baidu.com/c/c/forum/sign
```

| Body 参数 | 说明 |
|-----------|------|
| `BDUSS` | 登录凭证 |
| `fid` | 贴吧 ID |
| `kw` | 贴吧名称 |
| `tbs` | tbs 令牌 |
| `sign` | MD5 签名 |

响应 `error_code`：

| 值 | 说明 |
|----|------|
| `0` | 签到成功 |
| `160002` | 今日已签到 |
| `340006` | 贴吧已被屏蔽 |

### 1.3 签名算法

```
sign = MD5(sorted_params_concat + "tiebaclient!!!").upper()
```

---

## 二、阿里云盘 (Aliyun.py)

> 每日签到，获取累计签到天数和奖励信息。

### 刷新 Access Token

```
POST https://auth.aliyundrive.com/v2/account/token
```

| Body 参数 | 说明 |
|-----------|------|
| `grant_type` | 固定 `refresh_token` |
| `refresh_token` | 从环境变量 `ALIYUN_REFRESH_TOKEN` 读取 |

响应：`access_token`

---

### 获取签到列表 / 执行签到

```
POST https://member.aliyundrive.com/v1/activity/sign_in_list
```

| Header | 说明 |
|--------|------|
| `Authorization` | `{access_token}` |
| `Content-Type` | `application/json` |

响应：`result.signInCount`（累计天数）、`result.signInLogs[].reward`（奖励信息）

---

## 三、Bilibili (Bilibili.py)

> 每日任务：漫画签到、投币、观看、分享、银瓜子兑硬币。

### 用户导航信息

```
GET https://api.bilibili.com/x/web-interface/nav
```

响应：`uname`、`mid`、`isLogin`、`money`（硬币）、`level_info.current_exp`

---

### 今日经验明细

```
GET https://api.bilibili.com/x/member/web/exp/log?jsonp=jsonp
```

响应：`data.list[]` — 经验变更记录

---

### 漫画签到

```
POST https://manga.bilibili.com/twirp/activity.v1.Activity/ClockIn
```

| Body 参数 | 说明 |
|-----------|------|
| `platform` | 平台标识，如 `android` |

---

### 上报视频观看进度

```
POST http://api.bilibili.com/x/v2/history/report
```

| Body 参数 | 说明 |
|-----------|------|
| `aid` | 视频 avid |
| `cid` | 视频 cid |
| `progres` | 观看秒数，默认 `300` |
| `csrf` | bili_jct token |

---

### 分享视频

```
POST https://api.bilibili.com/x/web-interface/share/add
```

| Body 参数 | 说明 |
|-----------|------|
| `aid` | 视频 avid |
| `csrf` | bili_jct token |

---

### 获取关注列表

```
GET https://api.bilibili.com/x/relation/followings
```

| Query 参数 | 说明 |
|------------|------|
| `vmid` | 用户 UID |
| `pn` | 页码 |
| `ps` | 每页数量 |
| `order` | 排序 |
| `order_type` | 排序类型 |

---

### 获取 UP 主视频投稿

```
GET https://api.bilibili.com/x/space/arc/search
```

| Query 参数 | 说明 |
|------------|------|
| `mid` | UP 主 UID |
| `pn` | 页码 |
| `ps` | 每页数量 |
| `tid` | 分区 ID |
| `order` | 排序，默认 `pubdate` |

---

### 投币

```
POST https://api.bilibili.com/x/web-interface/coin/add
```

| Body 参数 | 说明 |
|-----------|------|
| `aid` | 视频 avid |
| `multiply` | 投币数 |
| `select_like` | 是否同时点赞，默认 `1` |
| `csrf` | bili_jct token |

---

### 获取直播瓜子状态

```
GET https://api.live.bilibili.com/pay/v1/Exchange/getStatus
```

响应：`data.silver`、`data.gold`、`data.coin`

---

### 获取分区视频列表

```
GET https://api.bilibili.com/x/web-interface/dynamic/region
```

| Query 参数 | 说明 |
|------------|------|
| `ps` | 数量 |
| `rid` | 分区 ID |

---

### 银瓜子兑换硬币

```
POST https://api.live.bilibili.com/xlive/revenue/v1/wallet/silver2coin
```

| Body 参数 | 说明 |
|-----------|------|
| `csrf` | bili_jct token |

---

## 四、森空岛 (skyland.py)

> 明日方舟 / 终末地每日签到，支持多账号多角色。需要 token（数美设备指纹 + HMAC 签名）。

### 获取设备 ID（数美）

```
POST https://fp-it.portal101.cn/deviceprofile/v4
```

| Body 参数 | 说明 |
|-----------|------|
| `appId` | 固定 `default` |
| `compress` | 固定 `2` |
| `data` | AES-128-CBC 加密的 gzip 压缩数据（16 进制） |
| `encode` | 固定 `5` |
| `ep` | RSA 公钥加密 uid 的 base64 |
| `organization` | 固定 `UWXspnCCJN4sfYlNfqps` |
| `os` | 固定 `web` |

加密流程：`DES 字段加密 → gzip → AES-128-CBC(key=MD5(uuid)[:16], iv=0102030405060708)`

---

### 获取 Grant Code

```
POST https://as.hypergryph.com/user/oauth2/v2/grant
```

| Body 参数 | 说明 |
|-----------|------|
| `appCode` | 固定 `4ca99fa6b56cc2ba` |
| `token` | 用户 token（环境变量） |
| `type` | 固定 `0` |

Headers：`dId`（设备 ID）

---

### 获取 Credential

```
POST https://zonai.skland.com/web/v1/user/auth/generate_cred_by_code
```

| Body 参数 | 说明 |
|-----------|------|
| `code` | grant code |
| `kind` | 固定 `1` |

响应：`data.cred`、`data.token`

---

### 获取绑定角色列表

```
GET https://zonai.skland.com/api/v1/game/player/binding
```

Headers：`cred`、`sign`、`platform`、`timestamp`、`dId`、`vName`

签名算法：`MD5(HMAC-SHA256(path + query/body + timestamp + header_json, token))`

---

### 明日方舟签到

```
POST https://zonai.skland.com/api/v1/game/attendance
```

| Body 参数 | 说明 |
|-----------|------|
| `gameId` | 游戏 ID |
| `uid` | 角色 UID |

响应：`data.awards[]` — 奖励列表 (`resource.name` × `count`)

---

### 终末地签到

```
POST https://zonai.skland.com/web/v1/game/endfield/attendance
```

Headers：额外需要 `sk-game-role: 3_{roleId}_{serverId}`、`referer`、`origin`

响应：`data.awardIds[]` + `data.resourceInfoMap` — 奖励信息

---

## 五、NodeSeek (Nodeseek.py)

> NodeSeek 论坛每日签到（使用 curl_cffi 模拟浏览器指纹）。

### 签到

```
POST https://www.nodeseek.com/api/attendance?random={true|false}
```

| Body 参数 | 说明 |
|-----------|------|
| `{}` | 空 JSON body |

Headers：`Cookie: {NS_COOKIE}`、`Content-Type: application/json`、`User-Agent`

响应：`success`（bool）、`message`（含"鸡腿"表示成功、"已完成签到"表示重复）

---

## 六、HelloGitHub (HelloGithub.py)

> 每月检查新刊发布，获取完整内容并分段推送到 Telegram。

### 获取最新期数信息

```
GET https://abroad.hellogithub.com/v1/periodical/
```

响应：`volumes[0].num`（最新期号）、`volumes[0].lastmod`

---

### 提取 buildId

```
GET https://hellogithub.com/periodical
```

从 HTML 中提取 `<script id="__NEXT_DATA__">` JSON 中的 `buildId`

---

### 获取指定期数详细内容

```
GET https://hellogithub.com/_next/data/{buildId}/zh/periodical/volume/{num}.json
```

响应：`pageProps.volumeData.data[]` — 按分类组织的项目列表

---

## 七、机场服务 (Airport.py)

> 通用机场签到框架，当前配置为「速鹰666」。

### 登录

```
POST {base_url}/auth/login
```

| Body 参数 | 说明 |
|-----------|------|
| `email` | 邮箱 |
| `passwd` | 密码 |
| `remember_me` | `on` |
| `code` | 验证码（留空） |

---

### 签到

```
POST {base_url}/user/checkin
```

响应：JSON，`msg` 字段为签到结果

---

### 获取用户信息 / 流量

```
GET {base_url}/user
```

响应：HTML 页面，用 XPath 提取流量信息

---

## 八、Bitwarden 备份 (Sync_Password.py)

> 自动登录 Bitwarden 导出密码数据，哈希比对后同步到 WebDAV。

### 登录 Bitwarden

```
POST {BITWARDEN_SERVER}/identity/connect/token
```

| Body 参数 | 说明 |
|-----------|------|
| `scope` | `api offline_access` |
| `client_id` | `web` |
| `grant_type` | `password` |
| `username` | 邮箱 |
| `password` | 密码 |

响应：`access_token`

---

### 同步获取数据

```
GET {BITWARDEN_SERVER}/api/sync?excludeDomains=true
```

Headers：`Authorization: Bearer {access_token}`

---

### 上传到 WebDAV

```
PUT {WEBDAV_SERVER}/123Pan/Password/{filename}
```

| Header | 说明 |
|--------|------|
| `Content-Type` | `application/octet-stream` |
| `Authorization` | HTTP Basic Auth |

---

## 九、SSL 证书检查 (SSL.py)

> 无外部 HTTP API 调用。通过 `ssl` + `socket` 标准库直连目标服务器获取证书信息。

---

## 十、Telegram Bot API (通用)

> 所有脚本共用的推送通知接口。

### 发送文本消息

```
POST https://api.telegram.org/bot{TOKEN}/sendMessage
```

| 参数 | 说明 |
|------|------|
| `chat_id` | 目标聊天 ID |
| `text` | 消息内容 |
| `parse_mode` | 解析模式：`HTML` / `Markdown` / `None` |
| `disable_web_page_preview` | 禁用链接预览，默认 `true` |

部分脚本使用可配置的 `TG_API_SERVER`（默认 `https://api.telegram.org`）。

---

### 发送文件（仅 Sync_Password.py）

```
POST https://api.telegram.org/bot{TOKEN}/sendDocument
```

| 参数 | 说明 |
|------|------|
| `chat_id` | 目标聊天 ID |
| `caption` | 文件说明文本 |
| `document` | 上传的文件（multipart） |

---

## 附录：环境变量一览

| 变量 | 使用脚本 | 说明 |
|------|----------|------|
| `TG_BOT_TOKEN` | 全部 | Telegram Bot Token |
| `TG_CHAT_ID` | 全部 | Telegram 接收 Chat ID |
| `TG_API_SERVER` | Airport, Sync_Password | Telegram API 服务器（可选） |
| `TIEBA_COOKIE` | Tieba | 百度贴吧 Cookie |
| `ALIYUN_REFRESH_TOKEN` | Aliyun | 阿里云盘 refresh_token |
| `BILIBILI_COOKIE` | Bilibili | B 站 Cookie（含 bili_jct） |
| `BILIBILI_COIN_NUM` | Bilibili | 每日目标投币数 |
| `BILIBILI_COIN_TYPE` | Bilibili | 投币来源类型 |
| `BILIBILI_SILVER2COIN` | Bilibili | 是否银瓜子兑硬币 |
| `SKYLAND_TOKEN` | skyland | 森空岛 token（逗号分隔多账号） |
| `NS_COOKIE` | Nodeseek | NodeSeek Cookie |
| `NS_RANDOM` | Nodeseek | 随机签到开关 |
| `NS_IMPERSONATE` | Nodeseek | curl_cffi 指纹 |
| `SUYING_USERNAME` | Airport | 速鹰666 邮箱 |
| `SUYING_PASSWORD` | Airport | 速鹰666 密码 |
| `BITWARDEN_SERVER` | Sync_Password | Bitwarden 服务器 |
| `BITWARDEN_USERNAME` | Sync_Password | Bitwarden 邮箱 |
| `BITWARDEN_PASSWORD` | Sync_Password | Bitwarden 密码 |
| `WEBDAV_SERVER` | Sync_Password | WebDAV 服务器 |
| `WEBDAV_USERNAME` | Sync_Password | WebDAV 用户名 |
| `WEBDAV_PASSWORD` | Sync_Password | WebDAV 密码 |
| `SSL_DOMAINS` | SSL | 要检查的域名（逗号分隔） |

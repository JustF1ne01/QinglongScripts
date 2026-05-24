# 小黑盒 (Heybox) API 文档

> 来源 HAR: `ido.gepush.com_2026_05_24_11_26_31.har` (登录后) + `data.xiaoheihe.cn_2026_05_24_11_40_01.har` (登录流程)  
> 客户端版本: v1.3.382 (Android)  
> 域名: `api.xiaoheihe.cn` / `data.xiaoheihe.cn` / `web.xiaoheihe.cn`

---

## 基础信息

| 项目 | 值 |
|------|-----|
| API 域名 | `https://api.xiaoheihe.cn` |
| 数据上报 | `https://data.xiaoheihe.cn` |
| Web 页面 | `https://web.xiaoheihe.cn` |
| 图片 CDN | `https://imgheybox.max-c.com`, `https://cdn.max-c.com` |
| 认证方式 | Cookie: `pkey` + `x_xhh_tokenid` |
| User-Agent | `Mozilla/5.0 ... ApiMaxJia/1.0` |
| RSA 加密库 | `jsencrypt@3.3.2` (从 `static.max-c.com` 加载) |

---

## 一、认证说明

Cookie 中两个关键字段：
- `pkey` — 设备标识（固定，已编码）
- `x_xhh_tokenid` — 登录凭证（有时效性，过期需重新登录）

每个请求 Query 参数通用：
- `heybox_id` — 用户 ID
- `imei` — 设备标识
- `device_info` — 设备型号
- `nonce` — 随机字符串
- `hkey` — 请求签名
- `_rnd` — 随机种子
- `os_type=Android` / `x_os_type=Android` / `x_client_type=mobile`
- `version=1.3.382` / `build=1076`
- `_time` — Unix 时间戳
- `time_zone=Asia/Shanghai` — 时区
- `x_app=heybox` / `channel=heybox_yingyongbao`

---

## 二、每日签到

### 执行签到 (v3 API)

```
GET https://api.xiaoheihe.cn/task/sign_v3/sign
```

**Response `state`:**

| state | 说明 |
|-------|------|
| `success` | 签到成功 |
| `ignore` | 今日已签到，无需重复 |
| `fail` | 签到失败 |

---

### 签到日历

```
GET https://api.xiaoheihe.cn/task/sign_list/
```

**Response:**
```json
{
  "status": "ok",
  "result": {
    "replenish_desc": "首次补签消耗100H币，最高1000H币...",
    "sign_list": [
      {"date": 1748016000, "is_sign": true},
      {"date": 1748102400, "is_sign": false}
    ]
  }
}
```

`date` 为当天 0 点 Unix 时间戳。

---

### 任务列表（含签到状态和奖励）

```
GET https://api.xiaoheihe.cn/task/list_v2/
```

**Response:**
```json
{
  "result": {
    "task_list": [{
      "tasks": [{
        "title": "签到",
        "state": "finish",
        "state_desc": "已完成",
        "award_desc_v2": [
          {"desc": "+40", "icon": "https://..."},
          {"desc": "+40", "icon": "https://..."},
          {"desc": "+1", "icon": "https://..."}
        ],
        "sign_in_streak": 1,
        "type": "sign"
      }]
    }]
  }
}
```

`state`: `finish`=已完成, `todo`=待完成

---

### 补签（消耗 H 币）

```
GET https://api.xiaoheihe.cn/task/replenish_sign_coin/
    ?date={timestamp}
```

**Response:** `{ "status": "ok", "result": { "cost": 200 } }`

---

## 三、登录流程（Cookie 刷新）

登录使用 **RSA 公钥加密** (jsencrypt@3.3.2 + PKCS1v15 padding)。

### RSA 公钥

从 APK `classes2.dex` 中 `LogHkLoginByIntent` 类提取：

```
-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC5se07mkN71qsSJHjZ2Z0+Z+4L
lLvf2sz7Md38VAa3EmAOvI7vZp3hbAxicL724ylcmisTPtZQhT/9C+25AELqy9PN
9JmzKpwoVTUoJvxG4BoyT49+gGVl6s6zo1byNoHUzTfkmRfmC9MC53HvG8GwKP5
xtcdptFjAIcgIR7oAWQIDAQAB
-----END PUBLIC KEY-----```
```

### 登录（不需要短信）

```
POST https://api.xiaoheihe.cn/account/login/
Content-Type: application/x-www-form-urlencoded

body: phone_num={RSA加密+base64+urlencode}&pwd={RSA加密+base64+urlencode}
```

成功后 Cookie 中 `x_xhh_tokenid` 自动更新。

### 短信验证码（仅忘记密码时用）

| 步骤 | 端点 | 说明 |
|------|------|------|
| 1 | `POST /account/get_pwd_code/` | 获取短信验证码 |
| 2 | `POST /account/get_pwd_sid/?code={SMS}` | 提交验证码获取 sid |
| 3 | `POST /account/modify_pwd_with_code/?sid={sid}` | 用 sid 修改密码 |

### 退出

```
GET /account/logout
```

**结论**: 脚本已内置 RSA 公钥，配置 `HEYBOX_PHONE` + `HEYBOX_PASSWORD` 即可自动登录刷新 Cookie。

---

## 四、账号相关

### 用户信息

```
GET https://api.xiaoheihe.cn/account/info/
```

**Response:**
```json
{
  "result": {
    "profile": { "nickname": "昵称", "avatar": "https://...", "gender": 1 },
    "account_detail": { "userid": "30182259", "level_info": { "level": 14 } },
    "steam_id_info": { "steamid": "76561199182334249", "nickname": "Steam昵称" }
  }
}
```

### 用户主页

```
GET https://api.xiaoheihe.cn/account/home_v2/
```

---

## 五、Steam 相关

### Steam 好友列表

```
GET https://api.xiaoheihe.cn/account/steam_friends_v2/
    ?userid={userid}&steam_id={steam_64bit_id}
```

**Response:**
```json
{
  "result": {
    "friends_count": 26,
    "friends": [{
      "steamid": "76561199183432534",
      "nickname": "ORANGE",
      "avatar": "https://...",
      "level": 8,
      "is_steam": 1,
      "has_heybox": 1,
      "heybox_info": { "userid": "34952525", "username": "ORANGE-II" }
    }]
  }
}
```

### Steam 玩家详情（官方 API）

```
GET http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/
    ?key={STEAM_API_KEY}&steamids={steamid1},{steamid2}
```

---

## 六、游戏库

```
GET https://api.xiaoheihe.cn/account/game_list/
    ?userid={userid}&steam_id={steam_id}&offset=0&limit=30
```

添加 `&sort=weeks` 按两周时长排序。

---

## 七、社区相关

| API | 说明 |
|-----|------|
| `GET /bbs/app/feeds` | 信息流 |
| `GET /bbs/app/profile/user/profile?userid=` | 用户资料 |
| `GET /bbs/app/api/notify/alert` | 通知提醒 |
| `GET /bbs/app/api/follow/alert` | 关注提醒 |
| `GET /bbs/app/profile/achieve/list` | 成就列表 |
| `GET /bbs/app/api/search/main_page/query_promote` | 搜索推广 |
| `GET /chatroom/v2/account/ws_id` | WebSocket 连接 ID |

---

## 八、配置/广告

| API | 说明 |
|-----|------|
| `GET /app/client/query_package_list` | 客户端包列表 |
| `GET /app/client/hot_fix` | 热修复 |
| `GET /account/get_ads_info_v2` | 广告配置 |
| `GET /account/popup_v2` | 弹窗配置 |
| `GET /account/tips_state` | 提示状态 |
| `GET /account/teen_mode/status` | 青少年模式 |
| `GET /account/privacy/version` | 隐私协议版本 |
| `GET /account/get_white_hostnames/` | 白名单域名 |
| `GET /account/get_async_js` | 异步 JS |

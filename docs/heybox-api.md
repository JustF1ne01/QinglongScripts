# 小黑盒 (Heybox) API 文档

> 来源 HAR: `ido.gepush.com_2026_05_24_11_26_31.har`  
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

---

## 一、认证说明

Cookie 中两个关键字段：
- `pkey` — 设备标识（固定，格式 `{timestamp}_{heybox_id}{random}`）
- `x_xhh_tokenid` — 登录凭证（base64 编码，有时效性）

每个请求 Query 参数通用：
- `heybox_id` — 用户 ID（如 `30182259`）
- `imei` — 设备标识（如 `a9381821da647661`）
- `device_info` — 设备型号（如 `25102RKBEC`）
- `nonce` — 随机字符串（每次请求随机生成）
- `hkey` — 请求签名（服务端校验）
- `_rnd` — 随机种子
- `os_type=Android` / `x_os_type=Android` / `x_client_type=mobile`
- `version=1.3.382`
- `build=1076`

---

## 二、每日签到

### 签到日历

```
GET https://api.xiaoheihe.cn/task/sign_list/
    ?heybox_id={heybox_id}
    &imei={imei}
    &device_info={device_info}
    &nonce={nonce}
    &hkey={hkey}
    &os_type=Android
    &version=1.3.382
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

`date` 为当天 0 点 Unix 时间戳，`is_sign` 表示是否已签到。

---

### 任务列表（含签到状态）

```
GET https://api.xiaoheihe.cn/task/list_v2/
    ?heybox_id={heybox_id}
    &imei={imei}
    &device_info={device_info}
    &nonce={nonce}
    &hkey={hkey}
    &os_type=Android
    &version=1.3.382
```

**Response:**
```json
{
  "status": "ok",
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
        "type": "sign",
        "desc": "(连续7天以上奖励更多)"
      }]
    }]
  }
}
```

`state`: `finish`=已完成, `todo`=待完成

---

### 补签

```
GET https://api.xiaoheihe.cn/task/replenish_sign_coin/
    ?date={timestamp}
    &heybox_id={heybox_id}
    &imei={imei}
    &device_info={device_info}
    &nonce={nonce}
    &hkey={hkey}
    &os_type=Android
    &version=1.3.382
```

**Response:** `{ "status": "ok", "result": { "cost": 200 } }`

花费 H 币补签历史未签到日期。`cost` 为消耗的 H 币数量。

---

## 三、账号相关

### 用户信息

```
GET https://api.xiaoheihe.cn/account/info/
    ?heybox_id={heybox_id}
    &imei={imei}
    &device_info={device_info}
    &nonce={nonce}
    &hkey={hkey}
```

**Response:**
```json
{
  "result": {
    "profile": {
      "nickname": "用户昵称",
      "avatar": "https://cdn.max-c.com/...",
      "gender": 1,
      "education": "本科",
      "career": "在校学生",
      "birthday": "883584000000"
    },
    "account_detail": {
      "userid": "30182259",
      "level_info": { "level": 14 },
      "signature": "签名"
    },
    "steam_id_info": {
      "steamid": "76561199182334249",
      "nickname": "Steam昵称"
    }
  }
}
```

### 用户主页

```
GET https://api.xiaoheihe.cn/account/home_v2/
    ?heybox_id={heybox_id}
    &imei={imei}
    &device_info={device_info}
    &nonce={nonce}
    &hkey={hkey}
```

### 绑定 Steam 账号

```
GET https://api.xiaoheihe.cn/account/bind_steam_id/?...
```

---

## 四、Steam 相关

### Steam 好友列表

```
GET https://api.xiaoheihe.cn/account/steam_friends_v2/
    ?userid={userid}
    &steam_id={steam_64bit_id}
    &heybox_id={heybox_id}
    &imei={imei}
    &device_info={device_info}
    &nonce={nonce}
    &hkey={hkey}
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
      "level_icon": "https://cdn.max-c.com/heybox/steam/profile/level/100.png",
      "is_steam": 1,
      "has_heybox": 1,
      "heybox_info": {
        "userid": "34952525",
        "username": "ORANGE-II",
        "avatar": "https://...",
        "level_info": { "level": 9 }
      }
    }]
  }
}
```

### Steam 玩家详情（官方 API）

```
GET http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/
    ?key={STEAM_API_KEY}
    &steamids={steamid1},{steamid2},...
```

Steam Web API，需要 Steam API Key。

---

## 五、游戏库

### 游戏列表

```
GET https://api.xiaoheihe.cn/account/game_list/
    ?userid={userid}
    &steam_id={steam_id}
    &offset=0
    &limit=30
    &heybox_id={heybox_id}
    &imei={imei}
    &device_info={device_info}
    &nonce={nonce}
    &hkey={hkey}
```

按最近游玩排序。添加 `&sort=weeks` 改为按两周时长排序。

---

## 六、社区相关

### 信息流 (Feed)

```
GET https://api.xiaoheihe.cn/bbs/app/feeds
    ?pull=1
    &is_first=1
    &list_ver=2
    &has_cache=1
    &heybox_id={heybox_id}
```

### 用户发帖/资料

```
GET https://api.xiaoheihe.cn/bbs/app/profile/user/profile
    ?userid={userid}
    &heybox_id={heybox_id}
```

### 通知提醒

```
GET https://api.xiaoheihe.cn/bbs/app/api/notify/alert
    ?heybox_id={heybox_id}
```

---

## 七、配置/广告

| API | 说明 |
|-----|------|
| `GET /app/client/query_package_list` | 查询客户端包列表 |
| `GET /account/get_ads_info_v2` | 获取广告配置 |
| `GET /account/popup_v2` | 弹窗配置 |
| `GET /account/tips_state` | 提示状态（新设备等） |
| `GET /account/teen_mode/status` | 青少年模式 |
| `GET /account/privacy/version` | 隐私协议版本 |

# 掌上无畏契约 (掌瓦) API 文档

> 来源 HAR: `oth.eve.mdt.qq.com_2026_05_24_00_42_06.har`
> 客户端版本: v2.6.0 (Android), QQ 登录

---

## 基础信息

| 项目 | 值 |
|------|-----|
| API 域名 | `https://app.mval.qq.com` |
| 图片 CDN | `https://game.gtimg.cn/images/val/agamezlk/` |
| 登录方式 | QQ 互联 (openid + access_token) |
| Cookie 关键字段 | `uin`, `openid`, `access_token`, `userId`, `accountType`, `appid`, `acctype`, `tid` |

---

## 一、认证流程

### 1. 刷新 Third Token（获取 access_token）

```
POST https://app.mval.qq.com/go/auth/refresh_third_token
  ?source_game_zone=agame
  &game_zone=agame
```

**Headers**: Cookie 中携带 `uin`, `openid`, `userId`, `appid`, `acctype`, `accountType`, `tid`

**Response**:
```json
{
  "result": 0,
  "msg": "success",
  "data": {
    "access_token": "0B20479BE87C90C4D47D22770C2BA4DD",
    "expired": 0,
    "time_interval": 0
  }
}
```

---

### 2. 获取 Client Tmp Ticket

```
POST https://app.mval.qq.com/go/auth/get_client_tmp_ticket
  ?source_game_zone=agame
  &game_zone=agame
```

**Response**:
```json
{
  "data": {
    "is_timeout": 0,
    "sk": "7954670f5ecd46e9bae485cfc064c534",
    "ctt": "FA2652ADDEC6D258689DED8933013DDA..."
  }
}
```

---

### 3. 获取 Web Ticket

```
POST https://app.mval.qq.com/go/auth/get_web_ticket
  ?source_game_zone=agame
  &game_zone=agame
```

**Response**:
```json
{
  "data": {
    "is_timeout": 0,
    "refresh_wt_span": 1800,
    "wt": "EEE018F2273BB63804884B1C0EE71559..."
  }
}
```

---

### 4. 刷新 Client Ticket

```
POST https://app.mval.qq.com/go/auth/refresh_client_ticket
  ?source_game_zone=agame
  &game_zone=agame
```

**Response**:
```json
{
  "data": {
    "ct_info": {
      "ct": "59A86CC1EC1C6C25BA8381C901FCC43A..."
    }
  }
}
```

---

### 5. 检查绑定关系

```
POST https://app.mval.qq.com/go/auth/check_bind_relation
  ?source_game_zone=agame
  &game_zone=agame
```

**Response**:
```json
{
  "result": 0,
  "jump_type": "loginSuccess"
}
```

---

### 6. 获取绑定账号列表

```
POST https://app.mval.qq.com/go/auth/bind_relation_list
  ?source_game_zone=agame
  &game_zone=agame
```

**Response**:
```json
{
  "data": {
    "list": [{
      "uin": "E15820289345C388A8F19205C6F0E06B",
      "nickName": "G",
      "selfUuid": "JA-8799caa88f324bcc-864118bed013a5c4",
      "type": 1,
      "iconUrl": "http://thirdqq.qlogo.cn/..."
    }]
  }
}
```

---

## 二、每日商店

### 获取每日商店

```
POST https://app.mval.qq.com/go/mlol_store/agame/user_store
  ?source_game_zone=agame
  &game_zone=agame
```

**Headers**:
- `Content-Type: application/json; charset=utf-8`
- `Cookie`: 含 `access_token`, `openid`, `userId`, `uin`, `tid`, `appid` 等

**Body**:
```json
{
  "scene": "{base64_encoded_scene_token}",
  "source_game_zone": "agame",
  "game_zone": "agame"
}
```

**Response**:
```json
{
  "result": 0,
  "data": [{
    "key": "dailystore",
    "title": "每日商店",
    "time": 26282,
    "end_ts": 1779580799,
    "cur_ts": 1779554517,
    "list": [{
      "goods_name": "RGX 11z Pro//3.0 狂徒",
      "goods_pic": "https://game.gtimg.cn/images/val/agamezlk/WeaponSkins/E81CE00C-49EA-B33D-693E-00A212C9D67D.png",
      "goods_id": "31ae0595-4ee7-57c8-f61c-2e808a6b77ed",
      "guid": "142BE691-42A0-C0A1-F6ED-57B3158DEF7E",
      "intent": "valpage://rn_page?...",
      "tips": "当前在游戏中购买",
      "rmb_price": "1590",
      "quality": "orange",
      "bg_image": "https://game.gtimg.cn/images/val/agamezlk/valapp/store/yellow.png",
      "showed": 1,
      "show_mask_quality": 1,
      "like_num": "19.4万玩家要",
      "skin_tag": ""
    }]
  }]
}
```

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `key` | string | 固定 `dailystore` |
| `time` | int | 剩余秒数 |
| `end_ts` | int | 商店过期 Unix 时间戳 |
| `cur_ts` | int | 当前时间戳 |
| `list[].goods_name` | string | 皮肤名称（编码问题需处理） |
| `list[].goods_pic` | string | 皮肤图片 URL（PNG 渲染图） |
| `list[].rmb_price` | string | 价格（点券） |
| `list[].quality` | string | 品质: `orange`(橙色/传奇), `purple`(紫色/史诗), `blue`(蓝色/稀有), `green`(绿色) |
| `list[].bg_image` | string | 品质背景图 URL |
| `list[].like_num` | string | 玩家点赞数 |
| `list[].tips` | string | 购买提示 |

### 品质颜色映射

| quality | 含义 | 背景图 |
|---------|------|--------|
| `orange` | 橙色/传奇 | `yellow.png` |
| `purple` | 紫色/史诗 | `pink.png` |
| `blue` | 蓝色/稀有 | `blue.png` |
| `green` | 绿色 | `green.png` |

---

### 礼包通知

```
POST https://app.mval.qq.com/go/mlol_store/agame/gift_notice_v2
  ?source_game_zone=agame
  &game_zone=agame
```

**Body**: `{}`
**Response**: `{ "result": 0, "data": [] }`

---

## 三、其他 API

### 获取用户信息

```
POST https://app.mval.qq.com/go/user_profile/query/user
  ?source_game_zone=agame
  &game_zone=agame
```

### 获取账号角色

```
GET https://app.mval.qq.com/go/account/getallgameroles
  ?source_game_zone=agame
  &game_zone=agame
```

### 推荐 Feed

```
GET https://app.mval.qq.com/go/mlol_news/recommend_feeds
  ?main_feeds=1
  &plat=android
  &zone=plat
  &channel=1
  &pic_size=384x204
  &waterflow=1
```

### 签到日历

```
POST https://app.mval.qq.com/go/agame/benefits/signin_carlender
  ?source_game_zone=agame
  &game_zone=agame
```

### 收益首页

```
POST https://app.mval.qq.com/go/agame/benefits/index
  ?source_game_zone=agame
  &game_zone=agame
```

---

## 四、Cookie 字段说明

| 字段 | 说明 |
|------|------|
| `clientType` | 固定 `9` |
| `uin` | QQ 号加密后的 uin |
| `appid` | QQ 互联 appid，固定 `102061775` |
| `acctype` | 登录类型，`qc` = QQ |
| `openid` | QQ 登录 openid |
| `access_token` | QQ 登录 access_token |
| `userId` | 掌瓦用户 UUID (如 `JA-xxx-xxx`) |
| `accountType` | 固定 `5` |
| `tid` | Web ticket（动态刷新） |

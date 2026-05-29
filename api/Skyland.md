# 森空岛签到 API 文档

## 脚本信息

- **文件名**: `skyland.py`
- **定时任务**: `0 8 * * *` (每天8:00执行)
- **功能**: 森空岛（Skland）自动签到，支持明日方舟、终末地等游戏

## 环境变量

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `SKLAND_TOKEN` | ✅ | 森空岛用户 Token |

## API 接口

### 1. 登录获取凭证

**请求:**
```
POST https://as.hypergryph.com/user/auth/v1/token_by_phone
```

**参数:**
```json
{
  "phone": "手机号",
  "code": "验证码"
}
```

**响应:**
```json
{
  "status": 0,
  "data": {
    "token": "user_token"
  }
}
```

### 2. 获取绑定角色列表

**请求:**
```
GET https://zonai.skland.com/api/v1/game/player/binding
```

**Headers:**
```
Authorization: {token}
```

**响应:**
```json
{
  "data": {
    "list": [
      {
        "channelId": 1,
        "uid": "player_uid",
        "gameId": "arknights",
        "name": "玩家名称"
      }
    ]
  }
}
```

### 3. 签到

**请求:**
```
POST https://zonai.skland.com/api/v1/game/player/sign
```

**参数:**
```json
{
  "gameId": "arknights",
  "uid": "player_uid",
  "channelId": 1
}
```

**响应:**
```json
{
  "data": {
    "awards": [
      {
        "name": "合成玉",
        "count": 100
      }
    ]
  }
}
```

## 支持的游戏

- `arknights` - 明日方舟
- `exastris` - 终末地

## 输出报告格式

```
🎮 森空岛签到报告

👤 账号: 玩家名称

🎮 明日方舟
✅ 签到成功，获得: 合成玉 × 100

🎮 终末地
✅ 签到成功，获得: 龙门币 × 5000

──────────────────
🕒 执行时间: 2026-05-29 08:00:00
```

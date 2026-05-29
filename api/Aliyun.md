# 阿里云盘签到 API 文档

## 脚本信息

- **文件名**: `Aliyun.py`
- **定时任务**: `0 9 * * *` (每天9:00执行)
- **功能**: 阿里云盘自动签到

## 环境变量

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `ALIYUN_TOKEN` | ✅ | 阿里云盘 refresh_token |

## API 接口

### 1. 刷新 Token

**请求:**
```
POST https://auth.aliyundrive.com/v2/account/token
```

**参数:**
```json
{
  "grant_type": "refresh_token",
  "refresh_token": "{refresh_token}"
}
```

**响应:**
```json
{
  "access_token": "new_access_token",
  "refresh_token": "new_refresh_token"
}
```

### 2. 签到

**请求:**
```
POST https://member.aliyundrive.com/v1/activity/sign_in_list
```

**Headers:**
```
Authorization: Bearer {access_token}
```

**响应:**
```json
{
  "result": {
    "signInCount": 7,
    "signInReward": true
  }
}
```

## 输出报告格式

```
🎯 阿里云盘签到报告

📅 本月签到: 7 天
🎁 签到奖励: 100 积分

──────────────────
🕒 执行时间: 2026-05-29 09:00:00
```

# 机场签到 API 文档

## 脚本信息

- **文件名**: `Airport.py`
- **定时任务**: `0 7 * * *` (每天7:00执行)
- **功能**: 机场自动签到

## 环境变量

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `AIRPORT_URL` | ✅ | 机场地址 |
| `AIRPORT_EMAIL` | ✅ | 机场邮箱 |
| `AIRPORT_PASSWORD` | ✅ | 机场密码 |

## API 接口

### 1. 用户登录

**请求:**
```
POST {AIRPORT_URL}/api/v1/passport/auth/login
```

**参数:**
```json
{
  "email": "用户邮箱",
  "password": "用户密码"
}
```

**响应:**
```json
{
  "data": {
    "auth_data": "token_string"
  }
}
```

### 2. 签到

**请求:**
```
POST {AIRPORT_URL}/api/v1/user/checkin
```

**Headers:**
```
Authorization: Bearer {auth_data}
```

**响应:**
```json
{
  "data": "签到成功，获取流量 1024MB"
}
```

## 输出报告格式

```
🎯 机场签到报告

👤 账号: user@example.com
✅ 签到成功，获取流量 1024MB

──────────────────
🕒 执行时间: 2026-05-29 07:00:00
```

# Bitwarden 密码同步 API 文档

## 脚本信息

- **文件名**: `Sync_Password.py`
- **定时任务**: `0 0 * * *` (每天0:00执行)
- **功能**: Bitwarden 密码库同步备份

## 环境变量

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `BITWARDEN_URL` | ❌ | Bitwarden 服务器地址 (默认官方) |
| `BITWARDEN_EMAIL` | ✅ | Bitwarden 邮箱 |
| `BITWARDEN_PASSWORD` | ✅ | Bitwarden 密码 |
| `BITWARDEN_CLIENT_ID` | ✅ | Bitwarden API Client ID |
| `BITWARDEN_CLIENT_SECRET` | ✅ | Bitwarden API Client Secret |

## API 接口

### 1. 获取 Token

**请求:**
```
POST https://identity.bitwarden.com/connect/token
```

**参数:**
```
grant_type=password
username={email}
password={password}
client_id={client_id}
client_secret={client_secret}
scope=api
deviceType=9
deviceIdentifier={uuid}
deviceName=chrome
```

**响应:**
```json
{
  "access_token": "token_string",
  "refresh_token": "refresh_token_string"
}
```

### 2. 同步密码库

**请求:**
```
GET https://api.bitwarden.com/sync
```

**Headers:**
```
Authorization: Bearer {access_token}
```

**响应:**
```json
{
  "profile": {...},
  "ciphers": [...],
  "folders": [...]
}
```

## 输出报告格式

```
🔒 Bitwarden 密码同步报告

✅ 同步成功
📁 同步项目: 150 个
📂 同步文件夹: 10 个
💾 备份已保存: /path/to/backup.json

──────────────────
🕒 执行时间: 2026-05-29 00:00:00
```

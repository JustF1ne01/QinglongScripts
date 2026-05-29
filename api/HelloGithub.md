# HelloGithub 签到 API 文档

## 脚本信息

- **文件名**: `HelloGithub.py`
- **定时任务**: `0 8 * * *` (每天8:00执行)
- **功能**: HelloGithub 月刊签到

## 环境变量

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `HELLOGITHUB_TOKEN` | ✅ | HelloGithub Token |

## API 接口

### 1. 签到

**请求:**
```
POST https://api.hellogithub.com/v1/intergral/sign
```

**Headers:**
```
Authorization: Bearer {token}
```

**响应:**
```json
{
  "success": true,
  "data": {
    "intergral": 10
  }
}
```

## 输出报告格式

```
🎯 HelloGithub 签到报告

✅ 签到成功，获得 10 积分

──────────────────
🕒 执行时间: 2026-05-29 08:00:00
```

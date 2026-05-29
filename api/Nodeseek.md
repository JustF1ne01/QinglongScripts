# Nodeseek 签到 API 文档

## 脚本信息

- **文件名**: `Nodeseek.py`
- **定时任务**: `0 8 * * *` (每天8:00执行)
- **功能**: Nodeseek 社区签到

## 环境变量

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `NODESEEK_COOKIE` | ✅ | Nodeseek Cookie |

## API 接口

### 1. 签到

**请求:**
```
POST https://www.nodeseek.com/board/sign
```

**Headers:**
```
Cookie: {NODESEEK_COOKIE}
```

**响应:**
```json
{
  "status": 0,
  "message": "签到成功",
  "data": {
    "reward": 10
  }
}
```

## 输出报告格式

```
🎯 Nodeseek 签到报告

✅ 签到成功，获得 10 金币

──────────────────
🕒 执行时间: 2026-05-29 08:00:00
```

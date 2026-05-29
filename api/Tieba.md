# 百度贴吧签到 API 文档

## 脚本信息

- **文件名**: `Tieba.py`
- **定时任务**: `0 0 * * *` (每天0:00执行)
- **功能**: 百度贴吧自动签到

## 环境变量

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `TIEBA_COOKIE` | ✅ | 百度贴吧 Cookie |

## API 接口

### 1. 获取关注贴吧列表

**请求:**
```
GET https://tieba.baidu.com/mo/q/newmoindex
```

**Headers:**
```
Cookie: {TIEBA_COOKIE}
```

**响应:**
```json
{
  "data": {
    "like_forum": [
      {
        "forum_name": "贴吧名称",
        "forum_id": 123456
      }
    ]
  }
}
```

### 2. 签到

**请求:**
```
POST https://tieba.baidu.com/sign/add
```

**参数:**
```json
{
  "ie": "utf-8",
  "kw": "贴吧名称",
  "tbs": "{tbs_token}"
}
```

**响应:**
```json
{
  "no": 0,
  "error": "success"
}
```

## 输出报告格式

```
🎯 百度贴吧签到报告

📊 签到结果: 10/10 个贴吧签到成功
✅ 签到成功: 吧1, 吧2, 吧3...
❌ 签到失败: 无

──────────────────
🕒 执行时间: 2026-05-29 00:00:00
```

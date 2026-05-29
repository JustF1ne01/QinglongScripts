# 阴阳师绘卷查询 API 文档

## 脚本信息

- **文件名**: `YysHuijuan.py`
- **定时任务**: `20 0 * * *` (每天0:20执行)
- **功能**: 阴阳师绘卷碎片查询，自动根据活动时间判断是否查询

## 环境变量

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `YYS_GL_UID` | ✅ | 阴阳师 GL UID |
| `YYS_GL_TOKEN` | ✅ | 阴阳师 GL Token |
| `YYS_URS_CREDENTIALS` | ✅ | URS 凭证 (格式: `id|token|account`) |

## API 接口

### 1. URS 登录

**请求:**
```
POST https://god.gameyw.netease.com/v1/app/base/user/login-by-urs-token
```

**参数:**
```json
{
  "urs": {
    "id": "urs_id",
    "token": "urs_token",
    "type": 10
  },
  "account": "account_name",
  "clientType": 50,
  "deviceId": "device_id",
  "os": "android",
  "version": "4.15.0"
}
```

**响应:**
```json
{
  "code": 200,
  "result": {
    "userInfo": {
      "user": {
        "uid": "user_uid",
        "nick": "用户昵称"
      }
    },
    "token": "new_token"
  }
}
```

### 2. 获取 GM SDK Token

**请求:**
```
POST https://god.gameyw.netease.com/v1/app/gameRole/getGmsdkToken
```

**参数:**
```json
{
  "roleId": "role_id",
  "server": "server_id",
  "appKey": "g37"
}
```

**响应:**
```json
{
  "code": 200,
  "result": {
    "gmSdkToken": "gm_sdk_token"
  }
}
```

### 3. 获取 SOP Session

**请求:**
```
GET https://game.16163.com/api/opd/sop/sopH5Tool/tokenIndex
```

**参数:**
```
application=god-gmsdk
profile=server
from=xiaoyi
sopId={sop_id}
token={gm_token}
```

**响应:**
```
重定向到 sopSession=xxx
```

### 4. 查询绘卷碎片

**请求:**
```
POST https://turing.gameyw.netease.com/sop-api/api/out/context/process
```

**参数:**
```json
{
  "contextId": "context_id",
  "sopSession": "sop_session",
  "async": true,
  "inputPayload": {
    "time": "2026-05-29"
  }
}
```

**响应:**
```json
{
  "message": "绘卷碎片·小：10/10 绘卷碎片·中：5 绘卷碎片·大：2"
}
```

## 绘卷分计算公式

```
绘卷分 = 小×10 + 中×20 + 大×100
```

## 输出报告格式

```
🎮 阴阳师绘卷碎片查询报告

📋 活动名称: SP天火命铃彦姬追忆绘卷活动
📅 活动时间: 2026-05-27 ~ 2026-06-16
📅 查询范围: 2026-05-27 ~ 2026-05-29

📊 查询结果
  📅 2026-05-27
    绘卷碎片·小: 10/10
    绘卷碎片·中: 5
    绘卷碎片·大: 2
    记录数: 3
    绘卷分: 300
  📅 2026-05-28
    绘卷碎片·小: 8/10
    绘卷碎片·中: 3
    绘卷碎片·大: 1
    记录数: 2
    绘卷分: 190

🏆 总计绘卷分: 490

──────────────────
🕒 查询时间: 2026-05-29 00:20:00
```

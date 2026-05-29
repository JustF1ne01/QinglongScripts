# Bilibili 每日任务 API 文档

## 脚本信息

- **文件名**: `Bilibili.py`
- **定时任务**: `0 0 * * *` (每天0:00执行)
- **功能**: Bilibili 每日任务（漫画签到、投币、观看视频、分享视频）

## 环境变量

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `BILIBILI_COOKIE` | ✅ | - | Bilibili Cookie |
| `BILIBILI_COIN_NUM` | ❌ | `0` | 每日投币数量 |
| `BILIBILI_COIN_TYPE` | ❌ | `1` | 投币来源 (1=关注, 2=热门) |
| `BILIBILI_SILVER2COIN` | ❌ | `false` | 是否兑换银瓜子 |

## API 接口

### 1. 获取用户信息

**请求:**
```
GET https://api.bilibili.com/x/web-interface/nav
```

**Headers:**
```
Cookie: {BILIBILI_COOKIE}
```

**响应:**
```json
{
  "data": {
    "uname": "用户名",
    "mid": 123456,
    "isLogin": true,
    "money": 100.5,
    "vipType": 2,
    "level_info": {
      "current_exp": 12345
    }
  }
}
```

### 2. 漫画签到

**请求:**
```
POST https://manga.bilibili.com/twirp/activity.v1.Activity/ClockIn
```

**参数:**
```json
{
  "platform": "android"
}
```

**响应:**
```json
{
  "code": 0,
  "msg": ""
}
```

### 3. 投币

**请求:**
```
POST https://api.bilibili.com/x/web-interface/coin/add
```

**参数:**
```json
{
  "aid": 123456,
  "multiply": 1,
  "select_like": 1,
  "cross_domain": "true",
  "csrf": "{bili_jct}"
}
```

### 4. 观看视频

**请求:**
```
POST http://api.bilibili.com/x/v2/history/report
```

**参数:**
```json
{
  "aid": 123456,
  "cid": 789,
  "progres": 300,
  "csrf": "{bili_jct}"
}
```

### 5. 分享视频

**请求:**
```
POST https://api.bilibili.com/x/web-interface/share/add
```

**参数:**
```json
{
  "aid": 123456,
  "csrf": "{bili_jct}"
}
```

### 6. 银瓜子兑换硬币

**请求:**
```
POST https://api.live.bilibili.com/xlive/revenue/v1/wallet/silver2coin
```

**参数:**
```json
{
  "csrf": "{bili_jct}"
}
```

## 输出报告格式

```
🎯 Bilibili 每日任务报告

👤 账号: 用户名

📖 漫画签到: ✅ 签到成功
📺 观看视频: ✅ 观看《视频标题》300秒
🔗 分享任务: ✅ 分享《视频标题》成功
💰 投币任务: 今日成功投币 5/5 个
💱 瓜子兑换: ✅ 银瓜子兑换硬币成功

📊 数据统计
⭐ 今日经验: 65
📈 当前经验: 12345
⏳ 升级还需: 100天

🥜 瓜子库存
🪙 硬币数量: 100.5
✨ 金瓜子数: 50
🥈 银瓜子数: 1000

──────────────────
🕒 执行时间: 2026-05-29 00:00:00
```

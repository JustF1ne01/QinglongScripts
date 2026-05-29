# Valorant 商店查询 API 文档

## 脚本信息

- **文件名**: `ValorantStore.py`
- **定时任务**: `0 8,20 * * *` (每天8:00和20:00执行)
- **功能**: Valorant 每日商店皮肤查询

## 环境变量

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `VALORANT_ACCESS_TOKEN` | ✅ | Riot Access Token |
| `VALORANT_ID_TOKEN` | ✅ | Riot ID Token |
| `VALORANT_PUUID` | ✅ | Riot PUUID |
| `VALORANT_REGION` | ✅ | 区域 (ap/na/eu) |
| `VALORANT_DEBUG` | ❌ | 调试模式 (true/false) |

## API 接口

### 1. 刷新 Token

**请求:**
```
POST https://auth.riotgames.com/token
```

**参数:**
```
grant_type=refresh_token
refresh_token={refresh_token}
client_id=play-valorant-web-prod
```

**响应:**
```json
{
  "access_token": "new_access_token",
  "id_token": "new_id_token",
  "refresh_token": "new_refresh_token"
}
```

### 2. 获取每日商店

**请求:**
```
GET https://pd.{region}.a.pvp.net/store/v2/storefront/{puuid}
```

**Headers:**
```
Authorization: Bearer {access_token}
X-Riot-Entitlements-JWT {entitlement_token}
```

**响应:**
```json
{
  "SkinsPanelLayout": {
    "SingleItemStoreOffers": [
      {
        "OfferID": "skin_id",
        "Cost": {
          "85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741": 1275
        }
      }
    ]
  }
}
```

## 输出报告格式

```
🎮 Valorant 每日商店报告

👤 账号: PlayerName

🔫 今日皮肤:
  1. Reaver Vandal - 1775 VP
  2. Prime Phantom - 1775 VP
  3. Ion Operator - 1775 VP
  4. Glitchpop Phantom - 2175 VP

──────────────────
🕒 查询时间: 2026-05-29 08:00:00
```

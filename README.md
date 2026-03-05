<div align="center">

# 🐉 QinglongScripts

**青龙面板自动任务订阅仓库，包含多个常用服务的自动签到/任务脚本。**

**A collection of auto check-in & task scripts for the Qinglong panel, covering various popular services.**

[![GitHub stars](https://img.shields.io/github/stars/CN-Grace/QinglongScripts?style=flat-square&logo=github)](https://github.com/CN-Grace/MQinglongScripts/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/CN-Grace/QinglongScripts?style=flat-square&logo=github)](https://github.com/CN-Grace/QinglongScripts/network/members)
[![GitHub license](https://img.shields.io/github/license/CN-Grace/QinglongScripts?style=flat-square)](https://github.com/CN-Grace/QinglongScripts/blob/main/LICENSE)

</div>

---

## 📥 订阅方式 | How to Subscribe

在青龙面板中添加订阅：

| 配置项 | 值 |
|:---:|:---|
| **名称** | `QinglongScripts` |
| **类型** | 公开仓库 |
| **链接** | `https://github.com/CN-Grace/QinglongScripts.git` |
| **定时类型** | crontab |
| **定时规则** | `0 0 * * *`（每天自动更新订阅） |
| **白名单** | 留空（拉取全部脚本） |
| **黑名单** | `notify.py`（通知模块，非定时任务） |

> 💡 添加订阅后，青龙面板会自动读取各脚本中的 `# cron` 注释来创建定时任务。

---

## 📜 脚本列表 | Script List

| 脚本 | 功能 | 定时规则 | 说明 |
|:---:|:---:|:---:|:---|
| ✈️ Airport.py | 机场签到 | `0 0 * * *` | 每天 0:00 |
| ☁️ Aliyun.py | 阿里云盘签到 | `0 0 * * *` | 每天 0:00 |
| 📺 Bilibili.py | B站每日任务 | `0 0 * * *` | 每天 0:00 |
| 🐙 HelloGithub.py | HelloGithub 月刊 | `0 8 1 * *` | 每月1日 8:00 |
| 💬 Nodeseek.py | Nodeseek 签到 | `0 0 * * *` | 每天 0:00 |
| 🔒 SSL.py | SSL 证书检查 | `0 0 * * *` | 每天 0:00 |
| 🔑 Sync_Password.py | Bitwarden 备份 | `0 0 * * *` | 每天 0:00 |
| 💬 Tieba.py | 百度贴吧签到 | `0 0 * * *` | 每天 0:00 |
| 🏝️ skyland.py | 森空岛签到 | `0 8 * * *` | 每天 8:00 |
| 🔔 notify.py | 通知模块 | — | 公共依赖，非定时任务 |

---

## ⚙️ 环境变量 | Environment Variables

请在青龙面板的「环境变量」中配置各脚本所需的变量，详见 [`.env.example`](.env.example) 文件。

---

## 📣 通知推送 | Notifications

所有脚本通过 `notify.py` 统一发送通知，支持以下 **23** 种渠道：

| # | 渠道 | 必填环境变量 | 可选环境变量 |
|:---:|:---|:---|:---|
| 1 | 🔔 Bark（iOS 推送） | `BARK_PUSH` | `BARK_ARCHIVE` `BARK_GROUP` `BARK_SOUND` `BARK_ICON` `BARK_LEVEL` `BARK_URL` |
| 2 | 🖥️ 控制台输出 | `CONSOLE` | — |
| 3 | 🤖 钉钉机器人 | `DD_BOT_TOKEN` `DD_BOT_SECRET` | — |
| 4 | 🪶 飞书机器人 | `FSKEY` | — |
| 5 | 💬 go-cqhttp | `GOBOT_URL` `GOBOT_QQ` | `GOBOT_TOKEN` |
| 6 | 📡 Gotify | `GOTIFY_URL` `GOTIFY_TOKEN` | `GOTIFY_PRIORITY` |
| 7 | 📲 iGot | `IGOT_PUSH_KEY` | — |
| 8 | 📢 Server酱 | `PUSH_KEY` | — |
| 9 | 🦌 PushDeer | `DEER_KEY` | `DEER_URL` |
| 10 | 💬 Synology Chat | `CHAT_URL` `CHAT_TOKEN` | — |
| 11 | ➕ PushPlus（微信推送） | `PUSH_PLUS_TOKEN` | `PUSH_PLUS_USER` `PUSH_PLUS_TEMPLATE` `PUSH_PLUS_CHANNEL` `PUSH_PLUS_WEBHOOK` `PUSH_PLUS_CALLBACKURL` `PUSH_PLUS_TO` |
| 12 | 🤖 微加机器人 | `WE_PLUS_BOT_TOKEN` | `WE_PLUS_BOT_RECEIVER` `WE_PLUS_BOT_VERSION` |
| 13 | 💬 Qmsg酱 | `QMSG_KEY` `QMSG_TYPE` | — |
| 14 | 🏢 企业微信应用 | `QYWX_AM` | `QYWX_ORIGIN` |
| 15 | 🏢 企业微信机器人 | `QYWX_KEY` | `QYWX_ORIGIN` |
| 16 | ✈️ Telegram | `TG_BOT_TOKEN` `TG_USER_ID` | `TG_API_HOST` `TG_PROXY_AUTH` `TG_PROXY_HOST` `TG_PROXY_PORT` |
| 17 | 🤖 智能微秘书 | `AIBOTK_KEY` `AIBOTK_TYPE` `AIBOTK_NAME` | — |
| 18 | 📧 SMTP 邮件 | `SMTP_SERVER` `SMTP_SSL` `SMTP_EMAIL` `SMTP_PASSWORD` `SMTP_NAME` | — |
| 19 | 📨 PushMe | `PUSHME_KEY` | `PUSHME_URL` |
| 20 | 🐧 CHRONOCAT（QQ 推送） | `CHRONOCAT_URL` `CHRONOCAT_QQ` `CHRONOCAT_TOKEN` | — |
| 21 | 🔗 自定义通知（Webhook） | `WEBHOOK_URL` `WEBHOOK_METHOD` | `WEBHOOK_BODY` `WEBHOOK_HEADERS` `WEBHOOK_CONTENT_TYPE` |
| 22 | 🔔 ntfy | `NTFY_TOPIC` | `NTFY_URL` `NTFY_PRIORITY` |
| 23 | 📱 WxPusher（微信推送） | `WXPUSHER_APP_TOKEN` + (`WXPUSHER_TOPIC_IDS` 或 `WXPUSHER_UIDS`) | — |

**通知附加选项：**

| 选项 | 环境变量 | 说明 |
|:---|:---|:---|
| 💬 一言（随机句子） | `HITOKOTO` | 通知内容末尾附加一条随机句子，默认启用，设为 `false` 可关闭 |

只需在环境变量中配置对应渠道即可启用，详见 [`.env.example`](.env.example) 文件。✅
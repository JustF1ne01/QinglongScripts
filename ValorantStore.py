#!/usr/bin/env python3
"""
cron: 15 8 * * *
new Env("掌瓦每日商店推送")
掌上无畏契约 每日商店自动推送
- 获取每日商店 4 款武器皮肤
- 文字报告推送至全部通知渠道
- 皮肤图片单独推送至 Telegram
"""

import json
import os
import tempfile
import requests
from datetime import datetime, timedelta, timezone

from utils import log_info, log_success, log_warning, log_error, beijing_time_str
from notify import send as notify_send

# ==================== 用户配置 ====================
VALORANT_COOKIE = os.environ.get("VALORANT_COOKIE", "")
TZ_BEIJING = timezone(timedelta(hours=8))

# 品质映射
QUALITY_MAP = {
    "orange": ("橙色/传奇", "🟧"),
    "purple": ("紫色/史诗", "🟪"),
    "blue": ("蓝色/稀有", "🟦"),
    "green": ("绿色", "🟩"),
    "white": ("白色", "⬜"),
}

API_BASE = "https://app.mval.qq.com"
COMMON_PARAMS = "source_game_zone=agame&game_zone=agame"


def create_session(cookie: str) -> requests.Session:
    """创建带 Cookie 的 Session"""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "mval/2.6.0.10062 Channel/5 Mozilla/5.0 (Linux; Android 16; wv) AppleWebKit/537.36",
        "Accept-Encoding": "gzip",
        "Content-Type": "application/json; charset=utf-8",
    })
    cookie_dict = {}
    for item in cookie.split(";"):
        item = item.strip()
        if "=" in item:
            k, v = item.split("=", 1)
            cookie_dict[k.strip()] = v.strip()
    requests.utils.add_dict_to_cookiejar(session.cookies, cookie_dict)
    return session


def api_post(session: requests.Session, path: str, body: dict = None) -> dict:
    """通用 POST 请求"""
    url = f"{API_BASE}{path}?{COMMON_PARAMS}"
    try:
        resp = session.post(url, json=body or {}, timeout=15)
        return resp.json()
    except Exception as e:
        log_error(f"API 请求失败 [{path}]: {e}")
        return {}


def refresh_token(session: requests.Session) -> str:
    """刷新 access_token，返回新的 token"""
    result = api_post(session, "/go/auth/refresh_third_token")
    if result.get("result") == 0:
        token = result.get("data", {}).get("access_token", "")
        if token:
            session.cookies.set("access_token", token, domain="app.mval.qq.com")
            log_success("access_token 刷新成功")
            return token
    log_warning(f"刷新 token 失败: {result.get('msg', '未知')}")
    return ""


def get_daily_store(session: requests.Session) -> tuple:
    """获取每日商店内容，返回 (items, end_ts)"""
    result = api_post(session, "/go/mlol_store/agame/user_store", {
        "scene": "",
        "source_game_zone": "agame",
        "game_zone": "agame",
    })
    if result.get("result") != 0:
        log_error(f"获取商店失败: {result.get('msg', '未知')}")
        return [], 0

    for section in result.get("data", []):
        if section["key"] == "dailystore":
            items = section.get("list", [])
            end_ts = section.get("end_ts", 0)
            log_success(f"获取到 {len(items)} 款每日商店皮肤")
            return items, end_ts
    return [], 0


def download_image(url: str) -> bytes:
    """下载图片"""
    try:
        resp = requests.get(url, timeout=15)
        if resp.ok:
            return resp.content
    except Exception:
        pass
    return b""


def send_telegram_photos(items: list) -> int:
    """通过 Telegram 发送皮肤图片，返回成功发送数量"""
    bot_token = os.environ.get("TG_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TG_USER_ID", "").strip() or os.environ.get("TG_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        return 0

    sent = 0
    for i, item in enumerate(items):
        name = item.get("goods_name", "未知")
        price = item.get("rmb_price", "?")
        quality = item.get("quality", "")
        quality_name, quality_emoji = QUALITY_MAP.get(quality, ("未知", "⬜"))
        image_url = item.get("goods_pic", "")

        if not image_url:
            continue

        caption = f"{quality_emoji} {name}\n💰 {price} 点券 | {quality_name}"

        image_data = download_image(image_url)
        if not image_data:
            log_warning(f"下载皮肤图片失败: {name}")
            continue

        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
            resp = requests.post(url, data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
                                files={"photo": (f"skin_{i+1}.png", image_data, "image/png")}, timeout=20)
            if resp.json().get("ok"):
                sent += 1
                log_success(f"已发送图片: {name}")
            else:
                log_warning(f"发送图片失败 [{name}]: {resp.json().get('description')}")
        except Exception as e:
            log_error(f"发送图片异常 [{name}]: {e}")

    return sent


def build_report(items: list, nickname: str, end_ts: int) -> str:
    """构建文字报告"""
    end_time = datetime.fromtimestamp(end_ts, tz=TZ_BEIJING).strftime("%Y-%m-%d %H:%M") if end_ts else "未知"

    lines = ["🔫 掌上无畏契约 每日商店", "", f"👤 账号: {nickname}", f"⏰ 刷新时间: {end_time}", "", "─" * 18, ""]

    for i, item in enumerate(items):
        name = item.get("goods_name", "未知")
        price = item.get("rmb_price", "?")
        quality = item.get("quality", "")
        likes = item.get("like_num", "")
        _, quality_emoji = QUALITY_MAP.get(quality, ("未知", "⬜"))

        lines.append(f"{i+1}. {quality_emoji} {name}")
        lines.append(f"   💰 {price} 点券 | ❤️ {likes}")
        lines.append("")

    lines.append("─" * 18)
    lines.append(f"🕒 执行时间: {beijing_time_str()}")
    return "\n".join(lines)


def main():
    if not VALORANT_COOKIE:
        log_error("未配置 VALORANT_COOKIE，请在环境变量中设置")
        notify_send("掌瓦每日商店 错误", "❌ 未配置 VALORANT_COOKIE")
        return

    session = create_session(VALORANT_COOKIE)

    # 刷新 token
    refresh_token(session)

    # 获取绑定账号
    bind_result = api_post(session, "/go/auth/bind_relation_list")
    bind_list = bind_result.get("data", {}).get("list", [])
    nickname = bind_list[0].get("nickName", "未知") if bind_list else "未知"
    log_info(f"绑定账号: {nickname}")

    # 获取每日商店
    items, end_ts = get_daily_store(session)
    if not items:
        log_warning("未获取到商店内容，可能今日未刷新")
        notify_send("掌瓦每日商店", "⚠️ 未获取到商店内容，请检查 Cookie 或稍后重试")
        return

    # 发送文字报告到所有通知渠道
    report = build_report(items, nickname, end_ts)
    notify_send("掌瓦每日商店", report)

    # 发送皮肤图片到 Telegram
    pic_count = send_telegram_photos(items)
    log_info(f"图片推送完成: {pic_count}/{len(items)} 张")


if __name__ == "__main__":
    main()

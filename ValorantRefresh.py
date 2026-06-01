#!/usr/bin/env python3
"""
cron: 0 */8 * * *
new Env("掌瓦Token刷新")
仅刷新 access_token 和 ct，不获取商店内容。
保持登录态活跃，防止 token 过期。
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime, timezone, timedelta

from utils import log_info, log_success, log_warning, log_error
from notifier import send as notify_send

# ==================== 用户配置 ====================
VALORANT_COOKIE = os.environ.get("VALORANT_COOKIE", "")
TZ_BEIJING = timezone(timedelta(hours=8))

API_BASE = "https://app.mval.qq.com"
COMMON_PARAMS = "source_game_zone=agame&game_zone=agame"
CT_FILE = Path(__file__).parent / ".valorant_ct"
AT_FILE = Path(__file__).parent / ".valorant_at"


def parse_cookie(cookie: str) -> dict:
    cookie_dict = {}
    for item in cookie.split(";"):
        item = item.strip()
        if "=" in item:
            k, v = item.split("=", 1)
            cookie_dict[k.strip()] = v.strip()
    return cookie_dict


def load_ct(cookie_dict: dict) -> str:
    ct = cookie_dict.get("ct", "")
    if ct:
        return ct
    if CT_FILE.exists():
        ct = CT_FILE.read_text().strip()
        if ct:
            return ct
    return ""


def save_ct(ct: str):
    CT_FILE.write_text(ct)


def load_at(cookie_dict: dict) -> str:
    at = cookie_dict.get("access_token", "")
    if at:
        return at
    if AT_FILE.exists():
        at = AT_FILE.read_text().strip()
        if at:
            return at
    return ""


def save_at(at: str):
    AT_FILE.write_text(at)


def create_session(cookie: str) -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "mval/2.6.0.10062 Channel/5 Mozilla/5.0 (Linux; Android 16; wv) AppleWebKit/537.36",
        "Accept-Encoding": "gzip",
        "Content-Type": "application/json; charset=utf-8",
    })
    cookie_dict = parse_cookie(cookie)
    cookie_dict.pop("ct", None)
    saved_at = load_at(cookie_dict)
    if saved_at:
        cookie_dict["access_token"] = saved_at
    requests.utils.add_dict_to_cookiejar(session.cookies, cookie_dict)
    return session


def api_post(session: requests.Session, path: str, body: dict = None) -> dict:
    url = f"{API_BASE}{path}?{COMMON_PARAMS}"
    try:
        resp = session.post(url, json=body or {}, timeout=15)
        try:
            return resp.json()
        except json.JSONDecodeError:
            text = resp.text.strip()
            decoder = json.JSONDecoder()
            obj, _ = decoder.raw_decode(text)
            return obj
    except Exception as e:
        log_error(f"API 请求失败 [{path}]: {e}")
        return {}


def refresh_token(session: requests.Session) -> str:
    cookie = {c.name: c.value for c in session.cookies}
    body = {
        "type": cookie.get("acctype", "qc"),
        "uuid": cookie.get("userId", ""),
        "openid": cookie.get("openid", ""),
        "source_game_zone": "agame",
        "game_zone": "agame",
    }
    result = api_post(session, "/go/auth/refresh_third_token", body)
    if result.get("result") == 0:
        token = result.get("data", {}).get("access_token", "")
        if token:
            session.cookies.set("access_token", token, domain="app.mval.qq.com")
            save_at(token)
            log_success("access_token 刷新成功")
            return token
    log_warning(f"刷新 token 失败: {result.get('msg', result.get('err_msg', '未知'))}")
    return ""


def refresh_web_ticket(session: requests.Session, ct: str) -> tuple:
    cookie = {c.name: c.value for c in session.cookies}
    user_id = cookie.get("userId", "")

    rct_body = {
        "config_params": {"lang_type": 0},
        "ct": ct,
        "local_is_new_user": 0,
        "user_id": user_id,
        "source_game_zone": "agame",
        "game_zone": "agame",
    }
    rct_result = api_post(session, "/go/auth/refresh_client_ticket", rct_body)
    if rct_result.get("result") != 0:
        log_warning(f"refresh_client_ticket 失败: {rct_result.get('msg', rct_result.get('err_msg', '未知'))}")
        return ct, False

    rct_data = rct_result.get("data", {})
    ct_info = rct_data.get("ct_info", rct_data)
    new_ct = ct_info.get("ct", "")
    wt = ct_info.get("wt", "")

    if new_ct:
        log_success(f"client ticket (ct) 刷新成功")
    if wt:
        tid_set = False
        for c in session.cookies:
            if c.name == "tid":
                c.value = wt
                tid_set = True
                break
        if not tid_set:
            session.cookies.set("tid", wt, domain="app.mval.qq.com", path="/")
        log_success(f"web ticket (tid) 刷新成功 (有效期 {ct_info.get('refresh_wt_span', '?')}s)")

    if not new_ct:
        log_warning("refresh_client_ticket 未返回新 ct")
        return ct, False

    ctt_body = {
        "config_params": {"lang_type": 0},
        "ct": new_ct,
    }
    api_post(session, "/go/auth/get_client_tmp_ticket", ctt_body)

    return new_ct, bool(wt)


def main():
    if not VALORANT_COOKIE:
        log_error("未配置 VALORANT_COOKIE")
        return

    cookie_dict = parse_cookie(VALORANT_COOKIE)
    ct = load_ct(cookie_dict)
    if not ct:
        log_error("未配置 ct")
        return

    session = create_session(VALORANT_COOKIE)
    now = datetime.now(TZ_BEIJING).strftime("%Y-%m-%d %H:%M")

    log_info(f"开始刷新 Token ({now})")

    # 先刷新 AT，再刷新 ct
    new_at = refresh_token(session)
    new_ct, ct_ok = refresh_web_ticket(session, ct)

    if new_ct and new_ct != ct:
        save_ct(new_ct)

    # 检查结果并通知
    if new_at and ct_ok:
        log_success("Token 刷新完成，登录态正常")
    elif new_at:
        log_warning("AT 刷新成功，但 ct 刷新失败")
        notify_send("掌瓦 Token 告警", f"⚠️ ct 刷新失败\n时间: {now}\n请尽快重新抓包")
    elif ct_ok:
        log_warning("ct 刷新成功，但 AT 刷新失败")
        notify_send("掌瓦 Token 告警", f"⚠️ access_token 刷新失败\n时间: {now}\n请尽快重新抓包")
    else:
        log_error("AT 和 ct 均刷新失败，登录态已失效")
        notify_send("掌瓦 Token 告警", f"❌ 登录态已失效\n时间: {now}\n请立即重新抓包更新 VALORANT_COOKIE")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
cron: 0 8 * * *
new Env("小黑盒每日签到")
小黑盒 (Heybox) 每日签到脚本
- 仅需手机号+密码即可运行（RSA 加密登录，无需抓包）
- 自动获取/刷新 Cookie，执行每日签到
"""

import base64
import os
import random
import string
import time
import requests
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding

from utils import log_info, log_success, log_warning, log_error, beijing_time_str
from notifier import send as notify_send

# ==================== 用户配置 ====================
HEYBOX_COOKIE = os.environ.get("HEYBOX_COOKIE", "")
HEYBOX_PHONE = os.environ.get("HEYBOX_PHONE", "")
HEYBOX_PASSWORD = os.environ.get("HEYBOX_PASSWORD", "")

# 从 APK (classes2.dex, LogHkLoginByIntent) 提取
RSA_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC5se07mkN71qsSJHjZ2Z0+Z+4L
lLvf2sz7Md38VAa3EmAOvI7vZp3hbAxicL724ylcmisTPtZQhT/9C+25AELqy9PN
9JmzKpwoVTUoJvxG4BoyT49+gGVl6s6zo1byNoHUzTfkmRfmC9MC53HvG8GwKP5
xtcdptFjAIcgIR7oAWQIDAQAB
-----END PUBLIC KEY-----"""

API_BASE = "https://api.xiaoheihe.cn"
TZ_BEIJING = timezone(timedelta(hours=8))
_RSA_KEY = serialization.load_pem_public_key(RSA_PUBLIC_KEY.encode())

# 从 HAR 成功请求复用的设备参数
_IMEI = "a9381821da647661"
_DEVICE_INFO = "25102RKBEC"
_UA = "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.118 Safari/537.36 ApiMaxJia/1.0"


def _rand_str(n: int = 32) -> str:
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(n))


def _rand_hex(n: int = 8) -> str:
    return "".join(random.choice("0123456789ABCDEF") for _ in range(n))


def _extract_cookie(key: str, default: str = "") -> str:
    for item in (HEYBOX_COOKIE or "").split(";"):
        item = item.strip()
        if "=" in item and item.split("=", 1)[0].strip() == key:
            return item.split("=", 1)[1].strip()
    return default


def _rsa_encrypt(plain: str) -> str:
    """RSA PKCS1v15 → base64 64字符换行 → URL 编码"""
    enc = _RSA_KEY.encrypt(plain.encode(), padding.PKCS1v15())
    b64 = base64.b64encode(enc).decode()
    wrapped = "\n".join(b64[i:i+64] for i in range(0, len(b64), 64))
    return quote(wrapped, safe="")


def _make_pkey(heybox_id: str) -> str:
    ts = time.time()
    raw = f"{ts:.4f}.{random.randint(10,99)}_{heybox_id}{_rand_str(12)}"
    return base64.b64encode(raw.encode()).decode().rstrip("=")


def create_session(heybox_id: str = "30182259") -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": _UA, "Accept-Encoding": "gzip"})
    if HEYBOX_COOKIE:
        for item in HEYBOX_COOKIE.split(";"):
            item = item.strip()
            if "=" in item:
                k, v = item.split("=", 1)
                s.cookies.set(k.strip(), v.strip(), domain="xiaoheihe.cn")
    else:
        s.cookies.set("pkey", _make_pkey(heybox_id), domain="xiaoheihe.cn")
    return s


def _common_params(heybox_id: str) -> str:
    ts = int(datetime.now(TZ_BEIJING).timestamp())
    return (
        f"heybox_id={heybox_id}&imei={_IMEI}&device_info={_DEVICE_INFO}"
        f"&nonce={_rand_str()}&hkey={_rand_hex()}&_rnd=14:{_rand_hex()}"
        f"&os_type=Android&x_os_type=Android&x_client_type=mobile"
        f"&os_version=16&version=1.3.382&build=1076"
        f"&_time={ts}&channel=heybox_yingyongbao&x_app=heybox"
    )


def _login_params() -> str:
    ts = int(datetime.now(TZ_BEIJING).timestamp())
    return (
        f"is_new_device=0&heybox_id=-1&imei={_IMEI}&device_info={_DEVICE_INFO}"
        f"&nonce={_rand_str()}&hkey={_rand_hex()}&_rnd=14:{_rand_hex()}"
        f"&os_type=Android&x_os_type=Android&x_client_type=mobile"
        f"&os_version=16&version=1.3.382&build=1076"
        f"&_time={ts}&dw=400&channel=heybox_yingyongbao&x_app=heybox"
        f"&time_zone=Asia/Shanghai"
    )


def api_get(session: requests.Session, path: str, heybox_id: str) -> dict:
    try:
        return session.get(f"{API_BASE}{path}?{_common_params(heybox_id)}", timeout=15).json()
    except Exception as e:
        log_error(f"GET {path}: {e}")
        return {}


def login(session: requests.Session) -> tuple:
    """返回 (heybox_id, nickname) 或 (None, 错误)"""
    if not HEYBOX_PHONE or not HEYBOX_PASSWORD:
        return None, "未配置手机号/密码"

    log_info("正在登录...")
    body = f"phone_num={_rsa_encrypt(HEYBOX_PHONE)}&pwd={_rsa_encrypt(HEYBOX_PASSWORD)}"
    url = f"{API_BASE}/account/login/?{_login_params()}"
    try:
        resp = session.post(url, data=body,
                           headers={"Content-Type": "application/x-www-form-urlencoded"},
                           timeout=15).json()
    except Exception as e:
        return None, str(e)

    if resp.get("status") != "ok":
        return None, resp.get("msg", "未知错误")

    p = resp.get("result", {}).get("profile", {})
    return p.get("heybox_id", ""), p.get("nickname", "未知")


def get_sign_status(session: requests.Session, hid: str) -> bool:
    r = api_get(session, "/task/sign_list/", hid)
    if r.get("status") != "ok":
        return False
    today_ts = int(datetime.now(TZ_BEIJING).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    for item in r.get("result", {}).get("sign_list", []):
        if item["date"] == today_ts:
            return item.get("is_sign", False)
    return False


def do_sign(session: requests.Session, hid: str) -> str:
    r = api_get(session, "/task/sign_v3/sign", hid)
    return r.get("result", {}).get("state", "fail") if r.get("status") == "ok" else "fail"


def get_task_info(session: requests.Session, hid: str) -> dict:
    r = api_get(session, "/task/list_v2/", hid)
    return r.get("result", {}) if r.get("status") == "ok" else {}


def get_nickname(session: requests.Session, hid: str) -> str:
    r = api_get(session, "/account/info/", hid)
    return r.get("result", {}).get("profile", {}).get("nickname", "未知")


def build_report(nickname: str, state: str, task_info: dict) -> str:
    L = ["🎮 小黑盒 每日签到", "", f"👤 账号: {nickname}"]
    if state == "success":
        L.append("✅ 签到状态: 签到成功!")
        for g in task_info.get("task_list", []):
            for t in g.get("tasks", []):
                if t.get("type") == "sign":
                    for a in t.get("award_desc_v2", []):
                        L.append(f"🎁 {a.get('desc', '')}")
                    L.append(f"🔥 连续签到: {t.get('sign_in_streak', '?')} 天")
                    break
            else:
                continue
            break
        else:
            L.append("🎁 奖励: 已自动发放")
    elif state == "ignore":
        L.append("⚠️ 签到状态: 今日已签到")
    else:
        L.append("❌ 签到状态: 签到失败")
    L += ["", "─" * 18, f"🕒 执行时间: {beijing_time_str()}"]
    return "\n".join(L)


def main():
    if not HEYBOX_PHONE and not HEYBOX_COOKIE:
        notify_send("小黑盒签到 错误", "❌ 请配置 HEYBOX_PHONE + HEYBOX_PASSWORD")
        return

    # 确定 heybox_id
    hid = _extract_cookie("heybox_id", "") or "30182259"
    session = create_session(hid)

    # 有 cookie 先验证
    nickname = "未知"
    if HEYBOX_COOKIE:
        nickname = get_nickname(session, hid)
        if nickname == "未知":
            log_warning("Cookie 过期，尝试登录...")
            hid, nickname = login(session) or (None, None)
            if not hid:
                notify_send("小黑盒签到 错误", "❌ Cookie 过期且登录失败")
                return
    else:
        hid, nickname = login(session) or (None, None)
        if not hid:
            notify_send("小黑盒签到 错误", f"❌ 登录失败: {nickname}")
            return

    log_info(f"账号: {nickname}")

    state = "ignore" if get_sign_status(session, hid) else do_sign(session, hid)
    if state == "fail":
        log_info("签到失败，重新登录后重试...")
        new_hid, new_nick = login(session) or (None, None)
        if new_hid:
            hid, nickname = new_hid, new_nick
            state = "ignore" if get_sign_status(session, hid) else do_sign(session, hid)

    ti = get_task_info(session, hid) or {}
    notify_send("小黑盒 签到报告", build_report(nickname, state, ti))
    log_success("推送完成")


if __name__ == "__main__":
    main()

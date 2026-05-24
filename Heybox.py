#!/usr/bin/env python3
"""
cron: 0 8 * * *
new Env("小黑盒每日签到")
小黑盒 (Heybox) 每日签到脚本
- 仅需手机号+密码即可运行（无需抓包 Cookie）
- RSA 加密登录，自动获取/刷新 Cookie
- 执行每日签到 (task/sign_v3/sign)
- 推送签到结果
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
HEYBOX_COOKIE = os.environ.get("HEYBOX_COOKIE", "")          # 可选，有则直接用
HEYBOX_PHONE = os.environ.get("HEYBOX_PHONE", "")            # 手机号（必填）
HEYBOX_PASSWORD = os.environ.get("HEYBOX_PASSWORD", "")      # 密码（必填）
HEYBOX_ID = os.environ.get("HEYBOX_ID", "")                  # 可选，自动获取
IMEI = os.environ.get("HEYBOX_IMEI", "")                     # 可选，自动生成

# 从 APK (classes2.dex, LogHkLoginByIntent) 提取的 RSA 1024-bit 公钥
RSA_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC5se07mkN71qsSJHjZ2Z0+Z+4L
lLvf2sz7Md38VAa3EmAOvI7vZp3hbAxicL724ylcmisTPtZQhT/9C+25AELqy9PN
9JmzKpwoVTUoJvxG4BoyT49+gGVl6s6zo1byNoHUzTfkmRfmC9MC53HvG8GwKP5
xtcdptFjAIcgIR7oAWQIDAQAB
-----END PUBLIC KEY-----"""

API_BASE = "https://api.xiaoheihe.cn"
TZ_BEIJING = timezone(timedelta(hours=8))
_RSA_KEY = serialization.load_pem_public_key(RSA_PUBLIC_KEY.encode())


def _random_str(length: int = 32) -> str:
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(length))


def _random_hex(length: int = 8) -> str:
    return "".join(random.choice("0123456789ABCDEF") for _ in range(length))


def _random_imei() -> str:
    return "a" + "".join(random.choice("0123456789abcdef") for _ in range(15))


def _generate_pkey(heybox_id: str = "30182259") -> str:
    """生成 pkey 设备指纹: {timestamp}.{rand}_{heybox_id}{rand} 的 base64"""
    ts = time.time()
    rand = str(random.randint(10, 99))
    rand_str = _random_str(12)
    raw = f"{ts:.4f}.{rand}_{heybox_id}{rand_str}"
    # URL-unsafe base64, strip padding
    return base64.b64encode(raw.encode()).decode().rstrip("=")


def _extract_from_cookie(key: str, default: str = "") -> str:
    for item in (HEYBOX_COOKIE or "").split(";"):
        item = item.strip()
        if "=" in item and item.split("=", 1)[0].strip() == key:
            return item.split("=", 1)[1].strip()
    return default


def _rsa_encrypt(plain: str) -> str:
    encrypted = _RSA_KEY.encrypt(plain.encode(), padding.PKCS1v15())
    return quote(base64.b64encode(encrypted).decode())


def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.118 Safari/537.36 ApiMaxJia/1.0",
        "Accept-Encoding": "gzip",
    })
    if HEYBOX_COOKIE:
        for item in HEYBOX_COOKIE.split(";"):
            item = item.strip()
            if "=" in item:
                k, v = item.split("=", 1)
                session.cookies.set(k.strip(), v.strip(), domain="xiaoheihe.cn")
    return session


def build_params(heybox_id: str, imei: str) -> str:
    params = [
        f"heybox_id={heybox_id}",
        f"imei={imei}",
        "device_info=25102RKBEC",
        f"nonce={_random_str(32)}",
        f"hkey={_random_hex(8)}",
        "os_type=Android",
        "x_os_type=Android",
        "x_client_type=mobile",
        "os_version=16",
        "version=1.3.382",
        "build=1076",
        f"_time={int(datetime.now(TZ_BEIJING).timestamp())}",
        "channel=heybox_yingyongbao",
        "x_app=heybox",
    ]
    return "&".join(params)


def api_get(session: requests.Session, path: str, heybox_id: str, imei: str) -> dict:
    url = f"{API_BASE}{path}?{build_params(heybox_id, imei)}"
    try:
        return session.get(url, timeout=15).json()
    except Exception as e:
        log_error(f"API 请求失败 [{path}]: {e}")
        return {}


def api_post(session: requests.Session, path: str, heybox_id: str, imei: str, data: str) -> dict:
    url = f"{API_BASE}{path}?{build_params(heybox_id, imei)}"
    try:
        return session.post(url, data=data,
                           headers={"Content-Type": "application/x-www-form-urlencoded"},
                           timeout=15).json()
    except Exception as e:
        log_error(f"API 请求失败 [{path}]: {e}")
        return {}


def login(session: requests.Session, imei: str) -> tuple:
    """RSA 加密登录，返回 (heybox_id, nickname) 或 (None, 错误信息)"""
    if not HEYBOX_PHONE or not HEYBOX_PASSWORD:
        return None, "未配置 HEYBOX_PHONE / HEYBOX_PASSWORD"

    log_info("正在登录...")
    encrypted_phone = _rsa_encrypt(HEYBOX_PHONE)
    encrypted_pwd = _rsa_encrypt(HEYBOX_PASSWORD)
    body = f"phone_num={encrypted_phone}&pwd={encrypted_pwd}"

    result = api_post(session, "/account/login/", "-1", imei, body)
    if result.get("status") != "ok":
        msg = result.get("msg", "未知错误")
        log_error(f"登录失败: {msg}")
        return None, msg

    profile = result.get("result", {}).get("profile", {})
    heybox_id = profile.get("heybox_id", "")
    nickname = profile.get("nickname", "未知")
    log_success(f"登录成功: {nickname} (ID: {heybox_id})")
    return heybox_id, nickname


def get_sign_status(session: requests.Session, heybox_id: str, imei: str) -> bool:
    result = api_get(session, "/task/sign_list/", heybox_id, imei)
    if result.get("status") != "ok":
        return False
    sign_list = result.get("result", {}).get("sign_list", [])
    today_start = datetime.now(TZ_BEIJING).replace(hour=0, minute=0, second=0, microsecond=0)
    today_ts = int(today_start.timestamp())
    for item in sign_list:
        if item["date"] == today_ts:
            return item.get("is_sign", False)
    return False


def do_sign(session: requests.Session, heybox_id: str, imei: str) -> str:
    result = api_get(session, "/task/sign_v3/sign", heybox_id, imei)
    if result.get("status") != "ok":
        log_error(f"签到请求失败: {result}")
        return "fail"
    state = result.get("result", {}).get("state", "fail")
    state_map = {"success": "签到成功 ✅", "ignore": "今日已签到，无需重复 ⚠️", "fail": "签到失败 ❌"}
    log_info(f"签到结果: {state_map.get(state, state)}")
    return state


def get_task_list(session: requests.Session, heybox_id: str, imei: str) -> dict:
    result = api_get(session, "/task/list_v2/", heybox_id, imei)
    return result.get("result", {}) if result.get("status") == "ok" else {}


def build_report(nickname: str, state: str, task_info: dict) -> str:
    lines = ["🎮 小黑盒 每日签到", "", f"👤 账号: {nickname}"]

    if state == "success":
        lines.append("✅ 签到状态: 签到成功!")
        for group in task_info.get("task_list", []):
            for task in group.get("tasks", []):
                if task.get("type") == "sign":
                    awards = task.get("award_desc_v2", [])
                    if awards:
                        lines.append("🎁 签到奖励:")
                        for a in awards:
                            lines.append(f"   {a.get('desc', '')}")
                    lines.append(f"🔥 连续签到: {task.get('sign_in_streak', '?')} 天")
                    break
        else:
            lines.append("🎁 奖励: 已自动发放")
    elif state == "ignore":
        lines.append("⚠️ 签到状态: 今日已签到")
    else:
        lines.append("❌ 签到状态: 签到失败")

    lines.append("")
    lines.append("─" * 18)
    lines.append(f"🕒 执行时间: {beijing_time_str()}")
    return "\n".join(lines)


def main():
    if not HEYBOX_PHONE and not HEYBOX_COOKIE:
        log_error("未配置 HEYBOX_PHONE 或 HEYBOX_COOKIE")
        notify_send("小黑盒签到 错误", "❌ 请配置 HEYBOX_PHONE + HEYBOX_PASSWORD，或 HEYBOX_COOKIE")
        return

    imei = IMEI or _random_imei()
    session = create_session()

    # 如果有 cookie 则直接使用，否则尝试登录
    heybox_id = HEYBOX_ID or _extract_from_cookie("heybox_id", "")
    nickname = "未知"

    if not heybox_id:
        # 设置一个临时 pkey 用于登录
        temp_pkey = _generate_pkey("30182259")
        session.cookies.set("pkey", temp_pkey, domain="xiaoheihe.cn")

        heybox_id, result = login(session, imei)
        if not heybox_id:
            notify_send("小黑盒签到 错误", f"❌ 登录失败: {result}")
            return
        nickname = result
    else:
        log_info(f"使用已有 Cookie, heybox_id={heybox_id}")
        # 先尝试获取账户信息验证 cookie 是否有效
        result = api_get(session, "/account/info/", heybox_id, imei)
        profile = result.get("result", {}).get("profile", {})
        if not profile:
            log_warning("Cookie 可能已过期，尝试重新登录...")
            temp_pkey = _generate_pkey("30182259")
            session.cookies.set("pkey", temp_pkey, domain="xiaoheihe.cn")
            session.cookies.clear("x_xhh_tokenid", domain="xiaoheihe.cn")

            new_id, nickname = login(session, imei)
            if new_id:
                heybox_id = new_id
            else:
                notify_send("小黑盒签到 错误", f"❌ Cookie 过期且登录失败")
                return
        else:
            nickname = profile.get("nickname", "未知")

    log_info(f"账号: {nickname} (ID: {heybox_id})")

    # 签到
    is_signed = get_sign_status(session, heybox_id, imei)
    state = "ignore" if is_signed else do_sign(session, heybox_id, imei)

    # 签到失败时重试登录
    if state == "fail" and HEYBOX_PHONE:
        log_info("签到失败，尝试重新登录...")
        new_id, _ = login(session, imei)
        if new_id:
            is_signed = get_sign_status(session, new_id, imei)
            state = "ignore" if is_signed else do_sign(session, new_id, imei)

    task_info = get_task_list(session, heybox_id, imei) or {}

    report = build_report(nickname, state, task_info)
    notify_send("小黑盒 签到报告", report)
    log_success("推送完成")


if __name__ == "__main__":
    main()

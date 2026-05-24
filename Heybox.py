#!/usr/bin/env python3
"""
cron: 0 8 * * *
new Env("小黑盒每日签到")
小黑盒 (Heybox) 每日签到脚本
- 执行每日签到 (task/sign_v3/sign)
- 支持 RSA 加密登录，自动刷新 Cookie
- 推送签到结果
"""

import base64
import os
import random
import string
import requests
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding

from utils import log_info, log_success, log_warning, log_error, beijing_time_str
from notifier import send as notify_send

# ==================== 用户配置 ====================
HEYBOX_COOKIE = os.environ.get("HEYBOX_COOKIE", "")
HEYBOX_PHONE = os.environ.get("HEYBOX_PHONE", "")      # 手机号（登录用）
HEYBOX_PASSWORD = os.environ.get("HEYBOX_PASSWORD", "") # 密码（登录用）
HEYBOX_ID = os.environ.get("HEYBOX_ID", "")
IMEI = os.environ.get("HEYBOX_IMEI", "")

# 从 APK (com.max.xiaoheihe) 提取的 RSA 公钥
RSA_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC5se07mkN71qsSJHjZ2Z0+Z+4L
lLvf2sz7Md38VAa3EmAOvI7vZp3hbAxicL724ylcmisTPtZQhT/9C+25AELqy9PN
9JmzKpwoVTUoJvxG4BoyT49+gGVl6s6zo1byNoHUzTfkmRfmC9MC53HvG8GwKP5
xtcdptFjAIcgIR7oAWQIDAQAB
-----END PUBLIC KEY-----"""

API_BASE = "https://api.xiaoheihe.cn"
TZ_BEIJING = timezone(timedelta(hours=8))

# 加载 RSA 公钥
_RSA_KEY = serialization.load_pem_public_key(RSA_PUBLIC_KEY.encode())


def _random_str(length: int = 32) -> str:
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(length))


def _random_hex(length: int = 8) -> str:
    return "".join(random.choice("0123456789ABCDEF") for _ in range(length))


def _extract_from_cookie(key: str, default: str = "") -> str:
    for item in HEYBOX_COOKIE.split(";"):
        item = item.strip()
        if "=" in item and item.split("=", 1)[0].strip() == key:
            return item.split("=", 1)[1].strip()
    return default


def _rsa_encrypt(plain: str) -> str:
    """RSA 公钥加密，返回 URL-encoded base64 字符串"""
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


def build_params(session: requests.Session = None) -> str:
    """构建通用 Query 参数"""
    heybox_id = HEYBOX_ID or _extract_from_cookie("heybox_id", "30182259")
    imei = IMEI or _extract_from_cookie("imei", "a9381821da647661")
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


def api_get(session: requests.Session, path: str) -> dict:
    url = f"{API_BASE}{path}?{build_params()}"
    try:
        resp = session.get(url, timeout=15)
        return resp.json()
    except Exception as e:
        log_error(f"API 请求失败 [{path}]: {e}")
        return {}


def api_post(session: requests.Session, path: str, data: str) -> dict:
    url = f"{API_BASE}{path}?{build_params()}"
    try:
        resp = session.post(url, data=data,
                           headers={"Content-Type": "application/x-www-form-urlencoded"},
                           timeout=15)
        return resp.json()
    except Exception as e:
        log_error(f"API 请求失败 [{path}]: {e}")
        return {}


def refresh_token(session: requests.Session) -> bool:
    """使用 RSA 加密的手机号和密码登录，刷新 Cookie"""
    if not HEYBOX_PHONE or not HEYBOX_PASSWORD:
        log_warning("未配置 HEYBOX_PHONE / HEYBOX_PASSWORD，跳过登录")
        return False

    log_info("正在登录刷新 Token...")
    encrypted_phone = _rsa_encrypt(HEYBOX_PHONE)
    encrypted_pwd = _rsa_encrypt(HEYBOX_PASSWORD)
    body = f"phone_num={encrypted_phone}&pwd={encrypted_pwd}"

    result = api_post(session, "/account/login/", body)
    if result.get("status") != "ok":
        log_error(f"登录失败: {result.get('msg', '未知错误')}")
        return False

    profile = result.get("result", {}).get("profile", {})
    nickname = profile.get("nickname", "未知")
    log_success(f"登录成功: {nickname}")

    # Cookie 已由 session 自动保存
    new_token = ""
    for c in session.cookies:
        if c.name == "x_xhh_tokenid":
            new_token = c.value
    if new_token:
        log_info(f"新 token: {new_token[:30]}...")
    return True


def get_sign_status(session: requests.Session) -> tuple:
    """检查今日签到状态"""
    result = api_get(session, "/task/sign_list/")
    if result.get("status") != "ok":
        return False, []

    sign_list = result.get("result", {}).get("sign_list", [])
    today_start = datetime.now(TZ_BEIJING).replace(hour=0, minute=0, second=0, microsecond=0)
    today_ts = int(today_start.timestamp())

    for item in sign_list:
        if item["date"] == today_ts:
            return item.get("is_sign", False), sign_list
    return False, sign_list


def do_sign(session: requests.Session) -> str:
    """执行签到 (v3 API)，返回 state"""
    result = api_get(session, "/task/sign_v3/sign")
    if result.get("status") != "ok":
        log_error(f"签到请求失败: {result}")
        return "fail"
    state = result.get("result", {}).get("state", "fail")
    state_map = {"success": "签到成功 ✅", "ignore": "今日已签到，无需重复 ⚠️", "fail": "签到失败 ❌"}
    log_info(f"签到结果: {state_map.get(state, state)}")
    return state


def get_task_list(session: requests.Session) -> dict:
    result = api_get(session, "/task/list_v2/")
    if result.get("status") != "ok":
        return {}
    return result.get("result", {})


def get_account_info(session: requests.Session) -> str:
    result = api_get(session, "/account/info/")
    if result.get("msg") == "":
        return result.get("result", {}).get("profile", {}).get("nickname", "未知")
    return "未知"


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
        lines.append("💡 将尝试重新登录刷新 Cookie")

    lines.append("")
    lines.append("─" * 18)
    lines.append(f"🕒 执行时间: {beijing_time_str()}")
    return "\n".join(lines)


def main():
    if not HEYBOX_COOKIE:
        log_error("未配置 HEYBOX_COOKIE")
        notify_send("小黑盒签到 错误", "❌ 未配置 HEYBOX_COOKIE")
        return

    session = create_session()
    nickname = get_account_info(session)
    log_info(f"账号: {nickname}")

    # 检查签到状态
    is_signed, _ = get_sign_status(session)

    state = "ignore"
    if not is_signed:
        log_info("今日未签到，开始执行签到...")
        state = do_sign(session)
    else:
        log_info("今日已签到，无需重复签到")

    task_info = get_task_list(session) or {}

    # 签到失败时尝试重新登录
    if state == "fail" and HEYBOX_PHONE:
        log_info("签到失败，尝试重新登录...")
        if refresh_token(session):
            # 重试签到
            is_signed, _ = get_sign_status(session)
            if not is_signed:
                state = do_sign(session)
            else:
                state = "ignore"
            task_info = get_task_list(session) or {}
            nickname = get_account_info(session)

    report = build_report(nickname, state, task_info)
    notify_send("小黑盒 签到报告", report)
    log_success("推送完成")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
cron: 0 8 * * *
new Env("小黑盒每日签到")
小黑盒 (Heybox) 每日签到脚本
- 获取签到日历和任务列表
- 执行每日签到
- 推送签到结果和奖励信息
"""

import os
import random
import string
import requests
from datetime import datetime, timezone, timedelta

from utils import log_info, log_success, log_warning, log_error, beijing_time_str
from notifier import send as notify_send

# ==================== 用户配置 ====================
HEYBOX_COOKIE = os.environ.get("HEYBOX_COOKIE", "")  # pkey=...;x_xhh_tokenid=...
HEYBOX_ID = os.environ.get("HEYBOX_ID", "")          # 小黑盒用户 ID
IMEI = os.environ.get("HEYBOX_IMEI", "")              # 设备标识

API_BASE = "https://api.xiaoheihe.cn"
TZ_BEIJING = timezone(timedelta(hours=8))


def _random_str(length: int = 32) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def _random_hex(length: int = 8) -> str:
    return "".join(random.choice("0123456789ABCDEF") for _ in range(length))


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


def build_params() -> str:
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
    ]
    return "&".join(params)


def _extract_from_cookie(key: str, default: str = "") -> str:
    for item in HEYBOX_COOKIE.split(";"):
        item = item.strip()
        if "=" in item and item.split("=", 1)[0].strip() == key:
            return item.split("=", 1)[1].strip()
    return default


def api_get(session: requests.Session, path: str) -> dict:
    """通用 GET 请求"""
    url = f"{API_BASE}{path}?{build_params()}"
    try:
        resp = session.get(url, timeout=15)
        return resp.json()
    except Exception as e:
        log_error(f"API 请求失败 [{path}]: {e}")
        return {}


def get_sign_status(session: requests.Session) -> tuple:
    """检查今日签到状态，返回 (is_signed_today, sign_streak, calendar)"""
    result = api_get(session, "/task/sign_list/")
    if result.get("status") != "ok":
        log_error(f"获取签到日历失败: {result}")
        return False, 0, []

    sign_list = result.get("result", {}).get("sign_list", [])
    today_start = datetime.now(TZ_BEIJING).replace(hour=0, minute=0, second=0, microsecond=0)
    today_ts = int(today_start.timestamp())

    is_signed = False
    for item in sign_list:
        if item["date"] == today_ts:
            is_signed = item.get("is_sign", False)
            break

    return is_signed, sign_list


def do_sign(session: requests.Session) -> bool:
    """执行签到，返回是否成功。尝试多个可能的签到入口"""
    # 方式1: 获取任务列表（有时会自动触发签到）
    result = api_get(session, "/task/list_v2/")
    if result.get("status") == "ok":
        log_info("已请求任务列表（触发签到）")

    # 方式2: 直接签到接口
    result2 = api_get(session, "/task/sign/")
    log_info(f"签到接口响应: {result2.get('status', result2.get('msg', 'unknown'))}")
    return result2.get("status") == "ok"


def get_task_list(session: requests.Session) -> dict:
    """获取任务列表，含签到奖励信息"""
    result = api_get(session, "/task/list_v2/")
    if result.get("status") != "ok":
        log_warning(f"获取任务列表失败: {result}")
        return {}
    return result.get("result", {})


def get_account_info(session: requests.Session) -> str:
    """获取用户昵称"""
    result = api_get(session, "/account/info/")
    if result.get("msg") == "":
        profile = result.get("result", {}).get("profile", {})
        return profile.get("nickname", "未知")
    return "未知"


def build_report(nickname: str, is_signed: bool,
                 task_info: dict, was_new_sign: bool) -> str:
    """构建签到报告"""
    lines = ["🎮 小黑盒 每日签到", "", f"👤 账号: {nickname}"]

    if was_new_sign:
        lines.append("✅ 签到状态: 签到成功!")

        # 提取签到奖励
        award_found = False
        for group in task_info.get("task_list", []):
            for task in group.get("tasks", []):
                if task.get("type") == "sign":
                    awards = task.get("award_desc_v2", [])
                    if awards:
                        award_found = True
                        lines.append(f"🎁 签到奖励:")
                        for a in awards:
                            lines.append(f"   {a.get('desc', '')}")
                    lines.append(f"🔥 连续签到: {task.get('sign_in_streak', '?')} 天")
                    break

        if not award_found:
            lines.append("🎁 奖励: 已自动发放")
    elif is_signed:
        lines.append("⚠️ 签到状态: 今日已签到")
        lines.append("🎁 无需重复签到")
    else:
        lines.append("❌ 签到状态: 未签到")
        lines.append("💡 请检查 Cookie 是否有效")

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
    is_signed, sign_list = get_sign_status(session)

    was_new_sign = False
    if not is_signed:
        log_info("今日未签到，开始执行签到...")
        was_new_sign = do_sign(session)

        # 重新检查签到状态确认
        is_signed, sign_list = get_sign_status(session)
        if is_signed:
            log_success("签到成功!")
            was_new_sign = True
        elif was_new_sign:
            log_success("签到接口返回成功")
        else:
            log_warning("签到未确认成功，请检查 Cookie 是否有效")
    else:
        log_info("今日已签到，无需重复签到")

    task_info = get_task_list(session)

    task_info = task_info or {}

    # 构建报告
    report = build_report(nickname, is_signed, task_info, was_new_sign)
    notify_send("小黑盒 签到报告", report)
    log_success("推送完成")


if __name__ == "__main__":
    main()

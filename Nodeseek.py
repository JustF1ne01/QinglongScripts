#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# new Env('Nodeseek签到')
# cron: 0 0 * * *
"""
NodeSeek-Signin (Single-file / Check-in only / Minimal)
=======================================================

功能：
- 仅使用 NS_COOKIE（单账号）执行 NodeSeek 签到
- NS_RANDOM：传给签到接口的 random 参数（true/false），用于是否“随机签到”（按仓库原脚本语义）
- 通知方式：通过 notify.py 统一通知模块

结构（按要求）：
1) shebang
2) 注释项目介绍（本段）
3) 导入外界库
4) 用户配置（不使用 config 变量名）
5) 各功能函数（不使用类）
6) 主函数 main()
"""

# ---------------- 导入外界库 ----------------
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple

import random
import time
import requests
from curl_cffi import requests as cffi_requests
from notify import send as notify_send


# ---------------- 用户配置（此处不要使用 cofig/config 变量） ----------------

# NodeSeek Cookie（单账号）
NS_COOKIE = os.getenv("NS_COOKIE", "").strip()

# “随机签到”开关：传给签到接口 random=true/false（按仓库原脚本语义）
NS_RANDOM = os.getenv("NS_RANDOM", "true").strip().lower()

# curl_cffi 指纹（尽量模拟浏览器）
NS_IMPERSONATE = os.getenv("NS_IMPERSONATE", "chrome110").strip()

# 时间显示：固定 UTC+8（北京时间）
TZ_GMT8 = timezone(timedelta(hours=8))


# ---------------- 各个功能的函数（不要使用类） ----------------

def _now_gmt8() -> datetime:
    return datetime.now(TZ_GMT8)


def _now_gmt8_str() -> str:
    return _now_gmt8().strftime("%Y-%m-%d %H:%M:%S")


def _curl_post_json(url: str, headers: Dict[str, str], body: dict, timeout: int = 30):
    return cffi_requests.post(
        url,
        headers=headers,
        json=body,
        timeout=timeout,
        impersonate=NS_IMPERSONATE,
    )


def _normalize_random_flag(v: str) -> str:
    v = (v or "").strip().lower()
    return v if v in ("true", "false") else "true"


def _sleep_jitter_before_checkin() -> int:
    """
    签到前随机延迟 0~30 分钟（含），降低自动化特征。
    返回实际延迟的秒数。
    """
    delay_seconds = random.randint(0, 30 * 60)
    if delay_seconds <= 0:
        print("签到前随机延迟: 0s（跳过）")
        return 0

    minutes = delay_seconds // 60
    seconds = delay_seconds % 60
    print(f"签到前随机延迟: {minutes}m {seconds}s ...")
    time.sleep(delay_seconds)
    return delay_seconds



def _format_result(ok: bool, status: str, message: str, elapsed_ms: int, delay_seconds: int) -> str:
    icon = "✅" if ok else "❌"
    delay_str = f"{delay_seconds // 60}m {delay_seconds % 60}s" if delay_seconds else "0s"
    lines = [
        f"{icon} 状态: {status}",
        f"🕒 时间: {_now_gmt8_str()} (UTC+8)",
        f"⏱️ 耗时: {elapsed_ms} ms",
        f"🕯️ 延迟: {delay_str} (签到前随机延迟)",
        f"📝 说明: {message}",
    ]
    return "\n".join(lines)


def nodeseek_checkin(cookie: str, ns_random: str) -> Tuple[bool, str, str]:
    """
    返回 (ok, status, message)

    特别处理：
- API 有时会返回 HTTP 500 但 body 表示 “今天已完成签到”，这应当视为成功（already）。
    """
    if not cookie:
        return False, "invalid", "无有效Cookie"

    random_flag = _normalize_random_flag(ns_random)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0"
        ),
        "origin": "https://www.nodeseek.com",
        "referer": "https://www.nodeseek.com/board",
        "Content-Type": "application/json",
        "Cookie": cookie,
    }

    url = f"https://www.nodeseek.com/api/attendance?random={random_flag}"

    try:
        start = datetime.now()
        r = _curl_post_json(url, headers=headers, body={}, timeout=25)
        elapsed_ms = int((datetime.now() - start).total_seconds() * 1000)

        body_text = ""
        data = None
        try:
            body_text = r.text or ""
            data = r.json()
        except Exception:
            data = None

        msg = ""
        success_flag = None
        if isinstance(data, dict):
            msg = str(data.get("message") or "")
            success_flag = data.get("success")

        if "鸡腿" in msg or bool(success_flag) is True:
            return True, "success", msg or "签到成功"

        if "已完成签到" in msg:
            return True, "already", msg

        if isinstance(data, dict) and data.get("status") == 404:
            return False, "invalid", msg or "Cookie已失效"

        if getattr(r, "status_code", 0) >= 400:
            if msg:
                return False, "error", msg
            snippet = body_text.strip()
            if len(snippet) > 200:
                snippet = snippet[:200] + "..."
            return False, "error", f"HTTP {r.status_code}: {snippet or '请求失败'}"

        return False, "fail", msg or "签到失败"

    except Exception as e:
        return False, "error", f"签到异常: {e}"


def main() -> int:
    print(f"[{_now_gmt8_str()}] NodeSeek 签到脚本启动（单账号 / 最小化）")

    if not NS_COOKIE:
        title = "NodeSeek 签到结果"
        content = _format_result(False, "invalid", "未配置 NS_COOKIE，无法签到。", 0, 0)
        print("\n" + content)
        notify_send(title, content)
        return 1

    # ✅ 新增：签到前随机延迟 0~30 分钟
    delay_seconds = _sleep_jitter_before_checkin()

    start = datetime.now()
    ok, status, message = nodeseek_checkin(NS_COOKIE, NS_RANDOM)
    elapsed_ms = int((datetime.now() - start).total_seconds() * 1000)

    title = f"NodeSeek 签到结果 @ {_now_gmt8_str()}"
    content = _format_result(ok, status, message, elapsed_ms, delay_seconds)

    print("\n" + content)
    notify_send(title, content)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
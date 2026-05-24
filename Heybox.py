#!/usr/bin/env python3
"""
cron: 0 8 * * *
new Env("小黑盒每日签到")
小黑盒 (Heybox) 每日签到脚本
- 仅需手机号+密码（RSA 加密登录，无需抓包）
- 自动计算 hkey 签名（算法来自 xhhBackCrack）
- 执行每日签到 (task/sign_v3/sign)
"""

import base64
import hashlib
import math
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
HEYBOX_COOKIE = os.environ.get("HEYBOX_COOKIE", "")  # 从 App/Web 抓包获取

# 从 APK 提取的全部 RSA 1024-bit 候选公钥（登录用，暂不可用）
_RSA_CANDIDATES = [
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC5se07mkN71qsSJHjZ2Z0+Z+4LlLvf2sz7Md38VAa3EmAOvI7vZp3hbAxicL724ylcmisTPtZQhT/9C+25AELqy9PN9JmzKpwoVTUoJvxG4BoyT49+gGVl6s6zo1byNoHUzTfkmRfmC9MC53HvG8GwKP5xtcdptFjAIcgIR7oAWQIDAQAB",
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDmKZL1TFWMfxggbo4qfXM5WsD0B3pUTjLCca/k/ESWqujQ2xTpESjUabHMEdEPnwmDtkXvIHJ14irPGulaXv6prpyPpt61dJqRYHvSmXr2x+HETNAIi0AHi+c/tE8LAKyHX2y4Zjv7iw48HidKv5+omug77Z/yTJqzhDvkkBteHQIDAQAB",
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC8UA4F9zfelx7qoRjTXEViE8WT60FBHJVl3T3/B+Nmljxiqa7H6GtOnmLFfpTVT+QdgBhxsU097DEBQhX8Z/9rVMp825T10jLefXly84/6p6B9Q0rNYX37zoWD5QT+5JWVgERX9P2o7fCXtlplLjv3dDXbzLdlWwdl53vtnAIidQIDAQAB",
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC9PkwyShdEmTYQE+KFGBlkzQLIzZlsHsltb6ROW96w18U+YTBcoQ6cDxKMHc1c1fbqHM2b2LRrC9q78ZaC4MeYXzFRl2MYU3d+0Qz++xiv31Y+idvmHUN2MXrmo5cfvuwI65t6F883fehNstbdCW2QFDS3jXkrY4DinRf4VGokdwIDAQAB",
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDENksAVqDoz5SMCZq0bsZwE+I3NjrANyTTwUVSf1+ec1PfPB4tiocEpYJFCYju9MIbawR8ivECbUWjpffZq5QllJg+19CB7V5rYGcEnb/M7CS3lFF2sNcRFJUtXUUAqyR3/l7PmpxTwObZ4DLG258dhE2vFlVGXjnuLs+FI2hg4QIDAQAB",
]
_RSA_KEY = None  # 登录成功后锁定

_API_BASE = "https://api.xiaoheihe.cn"
_TZ_BEIJING = timezone(timedelta(hours=8))

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
_IMEI = "a9381821da647661"
_DEVICE_INFO = "25102RKBEC"

# ==================== hkey 签名算法 (from xhhBackCrack) ====================
_CHARSET = "AB45STUVWZEFGJ6CH01D237IXYPQRKLMN89"


def _Vm(e):
    return (255 & ((e << 1) ^ 27)) if e & 128 else e << 1


def _qm(e):
    return _Vm(e) ^ e


def _dollar_m(e):
    return _qm(_Vm(e))


def _Ym(e):
    return _dollar_m(_qm(_Vm(e)))


def _Gm(e):
    return _Ym(e) ^ _dollar_m(e) ^ _qm(e)


def _Km_full(e_arr):
    e = list(e_arr)
    t = [0, 0, 0, 0]
    t[0] = _Gm(e[0]) ^ _Ym(e[1]) ^ _dollar_m(e[2]) ^ _qm(e[3])
    t[1] = _qm(e[0]) ^ _Gm(e[1]) ^ _Ym(e[2]) ^ _dollar_m(e[3])
    t[2] = _dollar_m(e[0]) ^ _qm(e[1]) ^ _Gm(e[2]) ^ _Ym(e[3])
    t[3] = _Ym(e[0]) ^ _dollar_m(e[1]) ^ _qm(e[2]) ^ _Gm(e[3])
    e[0], e[1], e[2], e[3] = t[0], t[1], t[2], t[3]
    return e


def _av(e, t, n):
    i = t[:n]  # n < 0 means slice to end-n
    r = ""
    for c in e:
        r += i[ord(c) % len(i)]
    return r


def _sv(e, t):
    r = ""
    for c in e:
        r += t[ord(c) % len(t)]
    return r


def _compute_hkey(path: str, timestamp: int, nonce: str) -> str:
    parts = [p for p in path.split("/") if p]
    normalized = "/" + "/".join(parts) + "/"
    comp1 = _av(str(timestamp), _CHARSET, -2)
    comp2 = _sv(normalized, _CHARSET)
    comp3 = _sv(nonce, _CHARSET)
    comps = [comp1, comp2, comp3]
    max_len = max(len(c) for c in comps)
    interleaved = ""
    for k in range(max_len):
        for c in comps:
            if k < len(c):
                interleaved += c[k]
    i_str = interleaved[:20]
    md5_hash = hashlib.md5(i_str.encode()).hexdigest()
    prefix = _av(md5_hash[:5], _CHARSET, -4)
    suffix_input = [ord(c) for c in md5_hash[-6:]]
    km_out = _Km_full(suffix_input)
    checksum = str(sum(km_out) % 100).zfill(2)
    return prefix + checksum


def _gen_nonce() -> str:
    raw = str(int(time.time() * 1000)) + str(random.random())
    return hashlib.md5(raw.encode()).hexdigest().upper()


def _gen_timestamp() -> int:
    return int(time.time())


def _build_url(path: str, heybox_id: str, extra_params: dict = None) -> str:
    """构建带 web hkey 签名的完整 URL（统一使用 web 参数）"""
    ts = _gen_timestamp()
    nonce = _gen_nonce()
    hkey = _compute_hkey(path, ts, nonce)

    params = {
        "heybox_id": heybox_id,
        "nonce": nonce,
        "hkey": hkey,
        "_time": str(ts),
        "os_type": "web",
        "app": "heybox",
        "client_type": "web",
        "version": "999.0.4",
        "x_client_type": "web",
        "x_app": "heybox_website",
        "x_os_type": "Windows",
        "device_info": "Chrome",
    }
    if extra_params:
        params.update(extra_params)

    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{_API_BASE}{path}?{qs}"


# ==================== 核心功能 ====================

def create_session(heybox_id: str = "30182259") -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": _UA, "Accept-Encoding": "gzip"})
    if HEYBOX_COOKIE:
        for item in HEYBOX_COOKIE.split(";"):
            item = item.strip()
            if "=" in item:
                k, v = item.split("=", 1)
                s.cookies.set(k.strip(), v.strip(), domain="xiaoheihe.cn")
    return s


def _rsa_encrypt(key, plain: str) -> str:
    enc = key.encrypt(plain.encode(), padding.PKCS1v15())
    b64 = base64.b64encode(enc).decode()
    wrapped = "\n".join(b64[i:i + 64] for i in range(0, len(b64), 64))
    return quote(wrapped, safe="")


def api_get(session: requests.Session, path: str, heybox_id: str, extra: dict = None) -> dict:
    url = _build_url(path, heybox_id, extra)
    try:
        return session.get(url, timeout=15).json()
    except Exception as e:
        log_error(f"GET {path}: {e}")
        return {}


def login(session: requests.Session) -> tuple:
    """用 RSA 加密登录，返回 (heybox_id, nickname)"""
    global _RSA_KEY
    if not HEYBOX_PHONE or not HEYBOX_PASSWORD:
        return None, "未配置手机号/密码"

    for idx, key_str in enumerate(_RSA_CANDIDATES):
        wrapped = "\n".join(key_str[i:i + 64] for i in range(0, len(key_str), 64))
        pem = f"-----BEGIN PUBLIC KEY-----\n{wrapped}\n-----END PUBLIC KEY-----"
        try:
            key = serialization.load_pem_public_key(pem.encode())
        except Exception as e:
            log_warning(f"Key {idx} 加载失败: {e}")
            continue

        body = f"phone_num={_rsa_encrypt(key, HEYBOX_PHONE)}&pwd={_rsa_encrypt(key, HEYBOX_PASSWORD)}"
        url = _build_url("/account/login/", "-1")
        log_info(f"尝试 Key {idx}...")
        try:
            resp = session.post(url, data=body,
                               headers={
                                   "Content-Type": "application/x-www-form-urlencoded",
                                   "Referer": "https://www.xiaoheihe.cn/",
                               },
                               timeout=15).json()
        except Exception as e:
            log_warning(f"Key {idx} 请求异常: {e}")
            continue

        msg = resp.get("msg", "")
        log_info(f"Key {idx} 响应: {msg}")
        if resp.get("status") == "ok":
            _RSA_KEY = key
            log_success(f"Key {idx} 登录成功!")
            p = resp.get("result", {}).get("profile", {})
            return p.get("heybox_id", ""), p.get("nickname", "未知")

    return None, "所有 Key 均登录失败"


def get_sign_status(session: requests.Session, hid: str) -> bool:
    r = api_get(session, "/task/sign_list/", hid)
    if r.get("status") != "ok":
        return False
    today_ts = int(datetime.now(_TZ_BEIJING).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
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
    if not HEYBOX_COOKIE:
        notify_send("小黑盒签到 错误", "❌ 请配置 HEYBOX_COOKIE")
        return

    hid = "30182259"
    for item in HEYBOX_COOKIE.split(";"):
        item = item.strip()
        if "=" in item and item.split("=", 1)[0].strip() == "heybox_id":
            hid = item.split("=", 1)[1].strip()

    session = create_session(hid)
    nickname = get_nickname(session, hid)
    if nickname == "未知":
        notify_send("小黑盒签到 错误", "❌ Cookie 无效，请重新抓包获取")
        return

    log_info(f"账号: {nickname}")
    state = "ignore" if get_sign_status(session, hid) else do_sign(session, hid)
    ti = get_task_info(session, hid) or {}
    notify_send("小黑盒 签到报告", build_report(nickname, state, ti))
    log_success("推送完成")


if __name__ == "__main__":
    main()

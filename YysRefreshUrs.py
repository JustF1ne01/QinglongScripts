#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
new Env("阴阳师URS凭证刷新")
通过网易邮箱密码登录获取新的URS凭证
"""
import hashlib, json, os, time, uuid, requests
from utils import log_info, log_success, log_warning, log_error

EMAIL = os.environ.get("YYS_EMAIL", "")
PASSWORD = os.environ.get("YYS_PASSWORD", "")
DEVICE_ID = "46758156facc4291a2acd9545b9ad90e"
SIGN_SECRET = "affa62e3b7376a0cbd20ea2f6c07072f"
VERSION = "4.18.2"
GOD_API = "https://god.gameyw.netease.com"
UNS_API = "https://sdk.reg.163.com"
ACCESS_ID = "f8740102324efeba30deb0f1d66a3ae3"


def gl_checksum(ct, cur, dev, nonce, src, token, uid, ver):
    return hashlib.sha1((SIGN_SECRET + ct + cur + dev + nonce + src + token + uid + ver).encode()).hexdigest()


def _headers(uid, token):
    t = int(time.time() * 1000)
    nonce = f"{t}_{uuid.uuid4().int}"
    cur = str(t)
    cs = gl_checksum("50", cur, DEVICE_ID, nonce, "URS", token, uid, VERSION)
    return {"Content-Type": "application/json; charset=utf-8", "User-Agent": "okhttp/4.9.1",
            "gl-clienttype": "50", "gl-curtime": cur, "gl-deviceid": DEVICE_ID, "gl-version": VERSION,
            "gl-nonce": nonce, "gl-channel": "open_tencent", "gl-activesquareid": "5bed6281d545682b8bb8a761",
            "gl-uid": uid, "gl-token": token, "gl-source": "URS", "gl-requesttime": str(t + 1), "gl-checksum": cs}


def try_uns_login():
    """尝试通过UNS SDK API登录"""
    log_info("尝试UNS邮箱密码登录...")
    pwd_md5 = hashlib.md5(PASSWORD.encode()).hexdigest()

    # 构建公共参数
    public_params = {
        "appId": ACCESS_ID,
        "product": "godlike_app",
        "platform": "android",
        "version": "1.6.4",
        "appVersion": VERSION,
        "systemVersion": 35,
        "model": "25102RKBEC",
        "resolution": "1080x2400",
        "carrier": "China Mobile",
        "network": "wifi",
        "emulator": False,
        "aId": hashlib.md5(EMAIL.encode()).hexdigest()[:16],
        "uniqueId": DEVICE_ID,
        "ua": "okhttp/4.9.1",
        "time": int(time.time() * 1000),
        "reqId": str(uuid.uuid4())
    }

    body = {
        "username": EMAIL,
        "pwd": pwd_md5,
        "p1": json.dumps(public_params),
        "p3": ACCESS_ID,
        "p4": "zh_CN"
    }

    try:
        resp = requests.post(f"{UNS_API}/uns/sdk/login/mail/pwd/v1/login",
            json=body, headers={"Content-Type": "application/json"}, timeout=15)
        data = resp.json()
        log_info(f"UNS响应: {json.dumps(data, ensure_ascii=False)}")

        if data.get("success"):
            token = data.get("data", {}).get("token", "")
            ticket = data.get("data", {}).get("ticket", "")
            log_success(f"UNS登录成功! token={token[:16]}...")
            return token, ticket
        else:
            log_warning(f"UNS登录失败: {data.get('msg', '')}")
            return None, None
    except Exception as e:
        log_error(f"UNS登录异常: {e}")
        return None, None


def try_godlike_login(urs_id, urs_token, account):
    """尝试通过GodLike API登录"""
    log_info("尝试GodLike URS登录...")

    for urs_type in [10, 1, 2, 5, 11, 20]:
        body = {
            "urs": {"id": urs_id, "token": urs_token, "type": urs_type},
            "account": account,
            "clientType": 50,
            "deviceId": DEVICE_ID,
            "os": "android",
            "version": VERSION,
            "osVersion": "16",
            "device": "25102RKBEC",
            "udid": DEVICE_ID[:16],
            "unisdkDeviceId": DEVICE_ID[:16],
            "autoLogin": True,
            "phoneUnbindCheck": False
        }

        try:
            resp = requests.post(f"{GOD_API}/v1/app/base/user/login-by-urs-token",
                json=body, headers=_headers("", ""), timeout=15)
            data = resp.json()
            code = data.get("code")
            log_info(f"  type={urs_type}: code={code}")

            if code == 200:
                result = data["result"]
                new_uid = result["userInfo"]["user"]["uid"]
                new_token = result["token"]
                nick = result["userInfo"]["user"].get("nick", "")
                log_success(f"GodLike登录成功! nick={nick}, uid={new_uid}")
                return new_uid, new_token
        except Exception as e:
            log_error(f"  type={urs_type}: {e}")

    return None, None


def try_ticket_exchange(ticket):
    """尝试通过ticket交换获取凭证"""
    if not ticket:
        return None, None

    log_info("尝试ticket交换...")
    try:
        resp = requests.post(f"{GOD_API}/v1/app/user/god-ticket/exchange/godAuthToken",
            json={"ticket": ticket, "clientType": 50, "deviceId": DEVICE_ID},
            headers=_headers("", ""), timeout=15)
        data = resp.json()
        log_info(f"ticket交换响应: code={data.get('code')}")

        if data.get("code") == 200:
            result = data["result"]
            return result.get("uid"), result.get("token")
    except Exception as e:
        log_error(f"ticket交换异常: {e}")

    return None, None


def update_env(name, value):
    """更新青龙环境变量"""
    try:
        # 先查找是否已存在
        resp = requests.get(f"http://localhost:5700/api/envs?searchValue={name}",
            headers={"Authorization": f"Bearer {os.environ.get('QL_TOKEN', '')}"}, timeout=10)
        # 这里需要实际的青龙API调用，暂时只打印
        log_info(f"请手动更新环境变量 {name}={value[:16]}...")
    except Exception:
        log_info(f"请手动更新环境变量 {name}={value[:16]}...")


def main():
    log_info("=" * 40)
    log_info("阴阳师URS凭证刷新")
    log_info("=" * 40)

    if not EMAIL or not PASSWORD:
        log_error("请设置 YYS_EMAIL 和 YYS_PASSWORD 环境变量")
        return

    log_info(f"邮箱: {EMAIL}")

    # 方案1: 尝试UNS登录
    uns_token, uns_ticket = try_uns_login()

    # 方案2: 如果UNS成功，尝试用获取的token登录GodLike
    if uns_token:
        uid, token = try_godlike_login(uns_token, uns_token, EMAIL)
        if uid:
            log_success("========== 刷新成功 ==========")
            log_success(f"YYS_GL_UID={uid}")
            log_success(f"YYS_GL_TOKEN={token}")
            update_env("YYS_GL_UID", uid)
            update_env("YYS_GL_TOKEN", token)
            return

    # 方案3: 尝试ticket交换
    if uns_ticket:
        uid, token = try_ticket_exchange(uns_ticket)
        if uid:
            log_success("========== ticket交换成功 ==========")
            log_success(f"YYS_GL_UID={uid}")
            log_success(f"YYS_GL_TOKEN={token}")
            return

    # 方案4: 尝试用现有URS凭证
    urs_creds = os.environ.get("YYS_URS_CREDENTIALS", "")
    if urs_creds:
        p = urs_creds.split("|")
        if len(p) == 3:
            log_info("尝试现有URS凭证...")
            uid, token = try_godlike_login(p[0], p[1], p[2])
            if uid:
                log_success("========== URS凭证有效 ==========")
                log_success(f"YYS_GL_UID={uid}")
                log_success(f"YYS_GL_TOKEN={token}")
                return

    log_error("========== 所有方案均失败 ==========")
    log_error("需要手动获取URS凭证:")
    log_error("1. 使用抓包工具抓取网易大神APP的登录请求")
    log_error("2. 从请求中提取 urs_id 和 urs_token")
    log_error("3. 更新青龙面板的 YYS_URS_CREDENTIALS 环境变量")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
UNS SDK Email/Password Login - Final Version
=============================================
Uses RSA public key extracted from libursandroidunity.so
"""
import hashlib, json, os, time, uuid, base64, random, string, requests

# RSA public key (1024-bit, extracted from APK)
RSA_PUBLIC_KEY_DER = base64.b64decode(
    "MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBAMnBrGFX33Iigp5h"
    "WGeDce2nwKYMBq12bMJIJC6MA+KUk58lEOpHFmSTdiqIIUxYxxr/uoThnoX+p/tz"
    "g5m1IisiOM8VtKqo3OuPuAiKlvBtbOK0lQ3QCkHsIDU6kSNoFJhEHgiOBxAEq45B"
    "S3DzeyK6JaGlOkIm27Um9UrHzMr/AgMBAAECgYEAs5Kg9ic7JyAWOBeWktOIpKlp"
    "q6EKlHvSQ33oTlGq55GsbrqT+qF5Cd3CEAsH8CcYWCyC++DAsqy9IO5olHeGx13+"
    "zqCL7JyUCrF4CQ5btSxAWNN1O6WEo9/9MaPlIe8gZ6IAC9jqhqG6+j0FR1uEQZOw"
    "VDiDwxr7w9IqZ6LC5WkCQQDzCALhZHJQZQlAgdrYkzRaa06Jm6bmV3eadIjKgfmS"
    "e6xwl0wS3LWg6deJN/OV/lhsTVp24VEZgbIgxQMMuiU7AkEA1IXRcWXdXVmgdnqc"
    "JA6lq3yL91YCLLe69cUahlDI4sQ4vL7okzSSc02oaWfTm/5imSW6BsYwHpvVyQfJ"
    "PfBFDQJAQ4GKK0lXZ3VpKH3paBcbh7Ie0qJlrb3F/yU3ieiohkPMFkowW1zrJpNN"
    "x1O/WX6Y2RxzcGoNuOQJsoiG3FYoWQJAMWJrOfuexft2wzFYqTRSIRhO+gmddcC4"
    "DDZiJIYPOEq6mHmQV+ymf26zTNMYpC4nwUi4Aqz5L5OsyQsrI1563QJASUinf6sK"
    "krBPmP+F4imfnSC0Y83KZcriW6dedJAK28TsvT2eg7A5dfgDdvIr85dv1zfRT7w4"
    "B31ycJgQJ09bZQ=="
)

ACCESS_ID = "f8740102324efeba30deb0f1d66a3ae3"
PRODUCT = "godlike_app"
UNS_VERSION = "1.6.4"
MAIL_LOGIN_URL = "https://sdk.reg.163.com/uns/sdk/login/mail/pwd/v1/login"

EMAIL = os.environ.get("YYS_EMAIL", "yuwenw112@163.com")
PASSWORD = os.environ.get("YYS_PASSWORD", "SYC5747zxh")


def md5_hex(s):
    return hashlib.md5(s.encode('utf-8')).hexdigest()


def sm4_encrypt(key_hex, iv_hex, plaintext):
    from gmssl import sm4 as sm4_mod
    key_bytes = bytes.fromhex(key_hex)
    iv_bytes = bytes.fromhex(iv_hex)
    crypt = sm4_mod.CryptSM4()
    crypt.set_key(key_bytes, sm4_mod.SM4_ENCRYPT)
    encrypted = crypt.cbc_encrypt(plaintext.encode('utf-8'), iv_bytes)
    return encrypted.hex()


def rsa_encrypt_pkcs1(public_key_der, plaintext):
    from Crypto.PublicKey import RSA
    from Crypto.Cipher import PKCS1_v1_5
    key = RSA.import_key(public_key_der)
    cipher = PKCS1_v1_5.new(key)
    # RSA encrypt in chunks
    key_size = key.size_in_bytes()
    max_chunk = key_size - 11
    plaintext_bytes = plaintext.encode('utf-8')
    encrypted_chunks = []
    for i in range(0, len(plaintext_bytes), max_chunk):
        chunk = plaintext_bytes[i:i + max_chunk]
        encrypted_chunks.append(cipher.encrypt(chunk))
    return b''.join(encrypted_chunks).hex().upper()


def do_login():
    # Build p1 parameters
    req_id = md5_hex(str(uuid.uuid4()))[:32]
    pwd_md5 = md5_hex(PASSWORD)
    device_id = "46758156facc4291a2acd9545b9ad90e"

    p1_params = {
        "username": EMAIL,
        "pwd": pwd_md5,
        "sn": "android",
        "dn": "",
        "rs": "",
        "ca": "",
        "nw": "wifi",
        "is": 0,
        "la": "",
        "lo": "",
        "im": "",
        "mac": "",
        "aid": "",
        "me": "",
        "md": "25102RKBEC",
        "uid": "",
        "idcf": device_id,
        "pdt": PRODUCT,
        "pv": "1.0.0",
        "yv": UNS_VERSION,
        "ydfp": device_id[:16],
        "appId": "",
        "product": PRODUCT,
        "platform": "android",
        "version": UNS_VERSION,
        "appVersion": "4.18.2",
        "systemVersion": 35,
        "model": "25102RKBEC",
        "hasResolution": "1080x2400",
        "carrier": "China Mobile",
        "network": "wifi",
        "emulator": 0,
        "aId": hashlib.md5(EMAIL.encode()).hexdigest()[:16],
        "uniqueId": device_id,
        "uniqueIdCf": device_id[:16],
        "packageSign": "test",
        "ydUniqueId": "",
        "pUniqueId": "",
        "ua": "okhttp/4.9.1",
        "time": int(time.time() * 1000),
        "reqId": req_id,
    }

    p1_json = json.dumps(p1_params, separators=(',', ':'))

    # Generate random SM4 key and IV
    sm4_key_hex = md5_hex(str(uuid.uuid4()))
    sm4_iv_hex = md5_hex(str(uuid.uuid4()))

    # SM4 encrypt p1
    p1_encrypted = sm4_encrypt(sm4_key_hex, sm4_iv_hex, p1_json)

    # RSA encrypt SM4 key+IV
    p2_json = json.dumps({"smkey": sm4_key_hex, "smIv": sm4_iv_hex}, separators=(',', ':'))
    p2_encrypted = rsa_encrypt_pkcs1(RSA_PUBLIC_KEY_DER, p2_json)

    # Build request body
    body = {
        "p1": p1_encrypted,
        "p2": p2_encrypted,
        "p3": ACCESS_ID,
        "p4": "zh_CN",
        "username": EMAIL,
        "pwd": pwd_md5,
    }

    print(f"[*] Login request:")
    print(f"    Email: {EMAIL}")
    print(f"    SM4 Key: {sm4_key_hex}")
    print(f"    SM4 IV: {sm4_iv_hex}")
    print(f"    P1 length: {len(p1_encrypted)}")
    print(f"    P2 length: {len(p2_encrypted)}")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": f"UNS-SDK/{UNS_VERSION} (Android)",
    }

    # Form-encode
    data = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in body.items())

    try:
        resp = requests.post(MAIL_LOGIN_URL, data=data, headers=headers, timeout=30)
        result = resp.json()
        print(f"\n[+] Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return result
    except Exception as e:
        print(f"\n[-] Error: {e}")
        return None


def godlike_login(urs_token, account):
    """Use UNS token to login to GodLike API"""
    import time as t, uuid as u
    DEVICE_ID = "46758156facc4291a2acd9545b9ad90e"
    SIGN_SECRET = "affa62e3b7376a0cbd20ea2f6c07072f"
    VERSION = "4.18.2"
    GOD_API = "https://god.gameyw.netease.com"

    def gl_checksum(ct, cur, dev, nonce, src, token, uid, ver):
        return hashlib.sha1((SIGN_SECRET + ct + cur + dev + nonce + src + token + uid + ver).encode()).hexdigest()

    def _headers(uid, token):
        ts = int(t.time() * 1000)
        nonce = f"{ts}_{u.uuid4().int}"
        cur = str(ts)
        cs = gl_checksum("50", cur, DEVICE_ID, nonce, "URS", token, uid, VERSION)
        return {"Content-Type": "application/json; charset=utf-8", "User-Agent": "okhttp/4.9.1",
                "gl-clienttype": "50", "gl-curtime": cur, "gl-deviceid": DEVICE_ID, "gl-version": VERSION,
                "gl-nonce": nonce, "gl-channel": "open_tencent", "gl-activesquareid": "5bed6281d545682b8bb8a761",
                "gl-uid": uid, "gl-token": token, "gl-source": "URS", "gl-requesttime": str(ts + 1), "gl-checksum": cs}

    body = {"urs": {"id": urs_token, "token": urs_token, "type": 10}, "account": account, "clientType": 50,
            "deviceId": DEVICE_ID, "os": "android", "version": VERSION, "osVersion": "16",
            "device": "25102RKBEC", "udid": DEVICE_ID[:16], "unisdkDeviceId": DEVICE_ID[:16],
            "autoLogin": True, "phoneUnbindCheck": False}

    resp = requests.post(f"{GOD_API}/v1/app/base/user/login-by-urs-token",
        json=body, headers=_headers("", ""), timeout=15)
    data = resp.json()
    print(f"GodLike login: code={data.get('code')}, errmsg={data.get('errmsg','')}")
    if data.get("code") == 200:
        result = data["result"]
        return result["userInfo"]["user"]["uid"], result["token"]
    return None, None


def main():
    print("=" * 60)
    print("UNS SDK Email/Password Login")
    print("=" * 60)

    result = do_login()

    if result and result.get("success"):
        token = result.get("data", {}).get("token", "")
        ticket = result.get("data", {}).get("ticket", "")
        print(f"\n[+] UNS login successful!")
        print(f"    Token: {token}")
        print(f"    Ticket: {ticket}")

        # Try GodLike login with the token
        if token:
            uid, gl_token = godlike_login(token, EMAIL)
            if uid:
                print(f"\n[+] GodLike login successful!")
                print(f"    YYS_GL_UID={uid}")
                print(f"    YYS_GL_TOKEN={gl_token}")
            else:
                print(f"\n[-] GodLike login failed, trying with ticket...")
                if ticket:
                    uid, gl_token = godlike_login(ticket, EMAIL)
                    if uid:
                        print(f"    YYS_GL_UID={uid}")
                        print(f"    YYS_GL_TOKEN={gl_token}")
    else:
        print(f"\n[-] UNS login failed")


if __name__ == "__main__":
    main()

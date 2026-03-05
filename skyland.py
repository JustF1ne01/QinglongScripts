#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# new Env('森空岛签到')
# cron 0 8 * * *

"""
森空岛（Skland）自动签到脚本
功能：
  1. 模拟数美设备指纹，生成设备ID（dId）
  2. 使用用户Token登录森空岛，获取凭证
  3. 遍历绑定角色，对明日方舟、终末地等游戏进行每日签到
  4. 签到结果通过notify.py统一推送（可选），推送格式美观
环境变量：
  TOKEN                森空岛Token，多个用英文逗号分隔
"""

import base64
import gzip
import hashlib
import hmac
import json
import logging
import os
import re
import time
import uuid
from urllib import parse

import requests
from notify import send as notify_send
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES
from cryptography.hazmat.primitives.ciphers.modes import CBC, ECB

# ==================== 用户配置（从环境变量读取）====================
TOKENS = os.environ.get("SKYLAND_TOKEN", "").split(",")

APP_CODE = "4ca99fa6b56cc2ba"               # 森空岛固定应用码
# ==============================================================

# ==================== 数美加密相关常量 ====================
SM_CONFIG = {
    "organization": "UWXspnCCJN4sfYlNfqps",
    "appId": "default",
    "publicKey": "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCmxMNr7n8ZeT0tE1R9j/mPixoinPkeM+k4VGIn/s0k7N5rJAfnZ0eMER+QhwFvshzo0LNmeUkpR8uIlU/GEVr8mN28sKmwd2gpygqj0ePnBmOW4v0ZVwbSYK+izkhVFk2V/doLoMbWy6b+UnA8mkjvg0iYWRByfRsK2gdl7llqCwIDAQAB",
    "protocol": "https",
    "apiHost": "fp-it.portal101.cn"
}
DES_RULE = {
    "appId": {"cipher": "DES", "is_encrypt": 1, "key": "uy7mzc4h", "obfuscated_name": "xx"},
    "box": {"is_encrypt": 0, "obfuscated_name": "jf"},
    "canvas": {"cipher": "DES", "is_encrypt": 1, "key": "snrn887t", "obfuscated_name": "yk"},
    "clientSize": {"cipher": "DES", "is_encrypt": 1, "key": "cpmjjgsu", "obfuscated_name": "zx"},
    "organization": {"cipher": "DES", "is_encrypt": 1, "key": "78moqjfc", "obfuscated_name": "dp"},
    "os": {"cipher": "DES", "is_encrypt": 1, "key": "je6vk6t4", "obfuscated_name": "pj"},
    "platform": {"cipher": "DES", "is_encrypt": 1, "key": "pakxhcd2", "obfuscated_name": "gm"},
    "plugins": {"cipher": "DES", "is_encrypt": 1, "key": "v51m3pzl", "obfuscated_name": "kq"},
    "pmf": {"cipher": "DES", "is_encrypt": 1, "key": "2mdeslu3", "obfuscated_name": "vw"},
    "protocol": {"is_encrypt": 0, "obfuscated_name": "protocol"},
    "referer": {"cipher": "DES", "is_encrypt": 1, "key": "y7bmrjlc", "obfuscated_name": "ab"},
    "res": {"cipher": "DES", "is_encrypt": 1, "key": "whxqm2a7", "obfuscated_name": "hf"},
    "rtype": {"cipher": "DES", "is_encrypt": 1, "key": "x8o2h2bl", "obfuscated_name": "lo"},
    "sdkver": {"cipher": "DES", "is_encrypt": 1, "key": "9q3dcxp2", "obfuscated_name": "sc"},
    "status": {"cipher": "DES", "is_encrypt": 1, "key": "2jbrxxw4", "obfuscated_name": "an"},
    "subVersion": {"cipher": "DES", "is_encrypt": 1, "key": "eo3i2puh", "obfuscated_name": "ns"},
    "svm": {"cipher": "DES", "is_encrypt": 1, "key": "fzj3kaeh", "obfuscated_name": "qr"},
    "time": {"cipher": "DES", "is_encrypt": 1, "key": "q2t3odsk", "obfuscated_name": "nb"},
    "timezone": {"cipher": "DES", "is_encrypt": 1, "key": "1uv05lj5", "obfuscated_name": "as"},
    "tn": {"cipher": "DES", "is_encrypt": 1, "key": "x9nzj1bp", "obfuscated_name": "py"},
    "trees": {"cipher": "DES", "is_encrypt": 1, "key": "acfs0xo4", "obfuscated_name": "pi"},
    "ua": {"cipher": "DES", "is_encrypt": 1, "key": "k92crp1t", "obfuscated_name": "bj"},
    "url": {"cipher": "DES", "is_encrypt": 1, "key": "y95hjkoo", "obfuscated_name": "cf"},
    "version": {"is_encrypt": 0, "obfuscated_name": "version"},
    "vpw": {"cipher": "DES", "is_encrypt": 1, "key": "r9924ab5", "obfuscated_name": "ca"}
}
BROWSER_ENV = {
    'plugins': 'MicrosoftEdgePDFPluginPortableDocumentFormatinternal-pdf-viewer1,MicrosoftEdgePDFViewermhjfbmdgcfjbbpaeojofohoefgiehjai1',
    'ua': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
    'canvas': '259ffe69',
    'timezone': -480,
    'platform': 'Win32',
    'url': 'https://www.skland.com/',
    'referer': '',
    'res': '1920_1080_24_1.25',
    'clientSize': '0_0_1080_1920_1920_1080_1920_1080',
    'status': '0011',
}
_PUBLIC_KEY = serialization.load_der_public_key(base64.b64decode(SM_CONFIG['publicKey']))
_DID_CACHE = None      # 设备ID缓存
# ==============================================================

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# ==============================================================

# ==================== 数美加密函数 ====================
def _des_encrypt(obj: dict) -> dict:
    """根据DES_RULE对字典中需要加密的字段进行DES加密并替换键名"""
    result = {}
    for key, value in obj.items():
        rule = DES_RULE.get(key)
        if not rule:
            result[key] = value
            continue
        if rule['is_encrypt'] == 1:
            # TripleDES ECB 加密（密钥可能为8字节，cryptography的TripleDES需要24字节，这里保留原样）
            cipher = Cipher(TripleDES(rule['key'].encode('utf-8')), ECB())
            data = str(value).encode('utf-8')
            # 补足8字节倍数（简单补零，非标准填充，但与原脚本一致）
            data += b'\x00' * (8 - len(data) % 8)
            encrypted = cipher.encryptor().update(data)
            result[rule['obfuscated_name']] = base64.b64encode(encrypted).decode('utf-8')
        else:
            result[rule['obfuscated_name']] = value
    logging.debug(f"DES加密后: {result}")
    return result


def _aes_encrypt(data: bytes, key: bytes) -> str:
    """AES-128 CBC加密，IV固定为'0102030405060708'，返回十六进制字符串"""
    iv = b'0102030405060708'
    cipher = Cipher(AES(key), CBC(iv))
    encryptor = cipher.encryptor()
    # 填充到16字节倍数（简单补零）
    pad_len = 16 - (len(data) % 16)
    data += b'\x00' * pad_len
    encrypted = encryptor.update(data) + encryptor.finalize()
    return encrypted.hex()


def _gzip_compress(obj: dict) -> bytes:
    """将字典压缩为gzip并base64编码"""
    json_str = json.dumps(obj, separators=(',', ':'), ensure_ascii=False)
    compressed = gzip.compress(json_str.encode('utf-8'), compresslevel=2, mtime=0)
    return base64.b64encode(compressed)


def _get_tn(obj: dict) -> str:
    """递归计算tn值（所有字段值拼接后做md5）"""
    sorted_keys = sorted(obj.keys())
    parts = []
    for k in sorted_keys:
        v = obj[k]
        if isinstance(v, (int, float)):
            parts.append(str(int(v * 10000)))
        elif isinstance(v, dict):
            parts.append(_get_tn(v))
        else:
            parts.append(str(v))
    return ''.join(parts)


def _get_smid() -> str:
    """生成SMID"""
    t = time.localtime()
    time_str = f"{t.tm_year}{t.tm_mon:02d}{t.tm_mday:02d}{t.tm_hour:02d}{t.tm_min:02d}{t.tm_sec:02d}"
    uid = str(uuid.uuid4())
    md5_uid = hashlib.md5(uid.encode()).hexdigest()
    base = time_str + md5_uid + '00'
    smsk = hashlib.md5(('smsk_web_' + base).encode()).hexdigest()[:14]
    return base + smsk + '0'


def get_device_id() -> str:
    """获取设备ID（dId），结果以'B'开头，并缓存"""
    global _DID_CACHE
    if _DID_CACHE:
        logging.info(f"使用缓存的设备ID: {_DID_CACHE}")
        return _DID_CACHE

    logging.info("开始生成设备ID...")
    uid = str(uuid.uuid4()).encode('utf-8')
    pri_id = hashlib.md5(uid).hexdigest()[:16]  # 16字节密钥
    # RSA加密uid
    ep = _PUBLIC_KEY.encrypt(uid, padding.PKCS1v15())
    ep_b64 = base64.b64encode(ep).decode('utf-8')

    # 构造待加密数据
    browser = BROWSER_ENV.copy()
    current_time = int(time.time() * 1000)
    browser.update({
        'vpw': str(uuid.uuid4()),
        'svm': current_time,
        'trees': str(uuid.uuid4()),
        'pmf': current_time
    })

    des_target = {
        **browser,
        'protocol': 102,
        'organization': SM_CONFIG['organization'],
        'appId': SM_CONFIG['appId'],
        'os': 'web',
        'version': '3.0.0',
        'sdkver': '3.0.0',
        'box': '',
        'rtype': 'all',
        'smid': _get_smid(),
        'subVersion': '1.0.0',
        'time': 0
    }
    # 计算tn
    des_target['tn'] = hashlib.md5(_get_tn(des_target).encode()).hexdigest()
    logging.debug(f"待加密数据: {des_target}")

    # 加密流程
    des_encrypted = _des_encrypt(des_target)
    compressed = _gzip_compress(des_encrypted)
    aes_encrypted = _aes_encrypt(compressed, pri_id.encode('utf-8'))

    # 请求设备ID
    url = f"https://{SM_CONFIG['apiHost']}/deviceprofile/v4"
    payload = {
        'appId': 'default',
        'compress': 2,
        'data': aes_encrypted,
        'encode': 5,
        'ep': ep_b64,
        'organization': SM_CONFIG['organization'],
        'os': 'web'
    }
    logging.info("向数美服务请求设备ID...")
    resp = requests.post(url, json=payload).json()
    if resp.get('code') != 1100:
        raise RuntimeError(f"获取设备ID失败: {resp}")
    _DID_CACHE = 'B' + resp['detail']['deviceId']
    logging.info(f"设备ID生成成功: {_DID_CACHE}")
    return _DID_CACHE


# ==================== 签到相关函数 ====================
def generate_signature(path: str, body_or_query: str, token: str, d_id: str) -> tuple:
    """
    生成签名和签名头字段
    :param path: 请求路径（不含域名）
    :param body_or_query: GET时为query字符串，POST时为JSON字符串
    :param token: 用户token
    :param d_id: 设备ID
    :return: (sign, header_ca) 其中header_ca包含platform,timestamp,dId,vName
    """
    timestamp = str(int(time.time()) - 2)   # 减2秒避免服务器时间校验
    header_ca = {
        'platform': '3',
        'timestamp': timestamp,
        'dId': d_id,
        'vName': '1.0.0'
    }
    # 注意：顺序必须与服务器一致，这里使用字典默认顺序（Python 3.7+ 保持插入顺序）
    header_str = json.dumps(header_ca, separators=(',', ':'))
    raw_string = path + body_or_query + timestamp + header_str
    logging.debug(f"待签名原始字符串: {raw_string}")
    hmac_sha256 = hmac.new(token.encode(), raw_string.encode(), hashlib.sha256).hexdigest()
    sign = hashlib.md5(hmac_sha256.encode()).hexdigest()
    logging.debug(f"生成的签名: {sign}")
    return sign, header_ca


def get_sign_headers(url: str, method: str, body, token: str, d_id: str, cred: str) -> dict:
    """
    为请求添加签名及其他必需头
    :param url: 完整URL
    :param method: 'get' 或 'post'
    :param body: POST的dict或None
    :param token: 用户token
    :param d_id: 设备ID
    :param cred: 用户凭证
    :return: 完整请求头字典
    """
    parsed = parse.urlparse(url)
    if method.lower() == 'get':
        sign, header_ca = generate_signature(parsed.path, parsed.query, token, d_id)
    else:
        body_str = json.dumps(body) if body else ''
        sign, header_ca = generate_signature(parsed.path, body_str, token, d_id)

    headers = {
        'cred': cred,
        'User-Agent': 'Mozilla/5.0 (Linux; Android 12; SM-A5560 Build/V417IR; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/101.0.4951.61 Safari/537.36; SKLand/1.52.1',
        'Accept-Encoding': 'gzip',
        'Connection': 'close',
        'X-Requested-With': 'com.hypergryph.skland',
        'sign': sign,
        **header_ca
    }
    logging.debug(f"生成的请求头: {headers}")
    return headers


def get_grant_code(token: str, d_id: str) -> str:
    """使用token换取grant code"""
    url = "https://as.hypergryph.com/user/oauth2/v2/grant"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 12; SM-A5560 Build/V417IR; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/101.0.4951.61 Safari/537.36; SKLand/1.52.1',
        'Accept-Encoding': 'gzip',
        'Connection': 'close',
        'dId': d_id,
        'X-Requested-With': 'com.hypergryph.skland'
    }
    payload = {
        'appCode': APP_CODE,
        'token': token,
        'type': 0
    }
    logging.info("正在获取grant code...")
    resp = requests.post(url, json=payload, headers=headers).json()
    if resp.get('status') != 0:
        raise RuntimeError(f"获取grant code失败: {resp.get('msg')}")
    code = resp['data']['code']
    logging.info(f"grant code获取成功: {code[:10]}...")
    return code


def get_cred(grant_code: str, d_id: str) -> dict:
    """使用grant code换取cred和token"""
    url = "https://zonai.skland.com/web/v1/user/auth/generate_cred_by_code"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 12; SM-A5560 Build/V417IR; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/101.0.4951.61 Safari/537.36; SKLand/1.52.1',
        'Accept-Encoding': 'gzip',
        'Connection': 'close',
        'dId': d_id,
        'X-Requested-With': 'com.hypergryph.skland'
    }
    payload = {'code': grant_code, 'kind': 1}
    logging.info("正在获取cred...")
    resp = requests.post(url, json=payload, headers=headers).json()
    if resp.get('code') != 0:
        raise RuntimeError(f"获取cred失败: {resp.get('message')}")
    cred_data = resp['data']
    logging.info(f"cred获取成功，token: {cred_data['token'][:10]}...")
    return cred_data  # 包含 'cred' 和 'token'


def get_binding_list(cred: str, token: str, d_id: str) -> list:
    """获取绑定角色列表，返回所有可签到角色"""
    url = "https://zonai.skland.com/api/v1/game/player/binding"
    headers = get_sign_headers(url, 'get', None, token, d_id, cred)
    logging.info("正在获取绑定角色列表...")
    resp = requests.get(url, headers=headers).json()
    if resp.get('code') != 0:
        if resp.get('message') == '用户未登录':
            logging.error("用户登录失效，请重新获取token")
        else:
            logging.error(f"获取角色列表失败: {resp.get('message')}")
        return []
    characters = []
    for game in resp['data']['list']:
        if game.get('appCode') not in ('arknights', 'endfield'):
            continue
        for char in game.get('bindingList', []):
            char['appCode'] = game['appCode']
            characters.append(char)
    logging.info(f"获取到 {len(characters)} 个可签到角色")
    return characters


def sign_arknights(character: dict, cred: str, token: str, d_id: str) -> list:
    """明日方舟签到"""
    url = "https://zonai.skland.com/api/v1/game/attendance"
    body = {
        'gameId': character.get('gameId'),
        'uid': character.get('uid')
    }
    headers = get_sign_headers(url, 'post', body, token, d_id, cred)
    logging.info(f"正在为角色 {character.get('nickName')} 进行明日方舟签到...")
    resp = requests.post(url, headers=headers, json=body).json()
    game_name = character.get('gameName', '明日方舟')
    channel = character.get('channelName', '')
    nickname = character.get('nickName') or ''
    if resp.get('code') != 0:
        msg = f"[{game_name}] 角色 {nickname}({channel}) 签到失败：{resp.get('message')}"
        logging.warning(msg)
        return [f"❌ {msg}"]
    awards = resp['data']['awards']
    award_text = ''.join([f"{a['resource']['name']}×{a.get('count',1)}" for a in awards])
    msg = f"[{game_name}] 角色 {nickname}({channel}) 签到成功，获得 {award_text}"
    logging.info(msg)
    return [f"✅ {msg}"]


def do_sign_endfield(role: dict, cred: str, token: str, d_id: str) -> requests.Response:
    """终末地单角色签到请求"""
    url = "https://zonai.skland.com/web/v1/game/endfield/attendance"
    headers = get_sign_headers(url, 'post', None, token, d_id, cred)
    headers.update({
        'Content-Type': 'application/json',
        'sk-game-role': f'3_{role["roleId"]}_{role["serverId"]}',
        'referer': 'https://game.skland.com/',
        'origin': 'https://game.skland.com/'
    })
    return requests.post(url, headers=headers)


def sign_endfield(character: dict, cred: str, token: str, d_id: str) -> list:
    """终末地签到（可能多个角色）"""
    roles = character.get('roles', [])
    game_name = character.get('gameName', '终末地')
    channel = character.get('channelName', '')
    results = []
    for role in roles:
        nickname = role.get('nickname') or ''
        logging.info(f"正在为角色 {nickname} 进行终末地签到...")
        resp = do_sign_endfield(role, cred, token, d_id)
        data = resp.json()
        if data.get('code') != 0:
            msg = f"[{game_name}] 角色 {nickname}({channel}) 签到失败：{data.get('message')}"
            logging.warning(msg)
            results.append(f"❌ {msg}")
        else:
            awards = []
            info_map = data['data']['resourceInfoMap']
            for award_id in data['data']['awardIds']:
                aid = award_id['id']
                awards.append(f"{info_map[aid]['name']}×{info_map[aid]['count']}")
            msg = f"[{game_name}] 角色 {nickname}({channel}) 签到成功，获得 {','.join(awards)}"
            logging.info(msg)
            results.append(f"✅ {msg}")
    return results


def process_token(user_token: str, d_id: str, account_index: int) -> list:
    """处理单个token的签到流程，返回该token所有角色的签到日志（带表情）"""
    logs = []
    try:
        logging.info(f"===== 开始处理第 {account_index} 个账号 =====")
        grant_code = get_grant_code(user_token, d_id)
        cred_data = get_cred(grant_code, d_id)
        cred = cred_data['cred']
        token = cred_data['token']   # 注意：这是cred接口返回的token，不是用户输入的token
        characters = get_binding_list(cred, token, d_id)
        if not characters:
            logs.append("ℹ️ 该账号下无绑定角色或无支持签到的游戏")
            return logs
        for char in characters:
            if char['appCode'] == 'arknights':
                logs.extend(sign_arknights(char, cred, token, d_id))
            elif char['appCode'] == 'endfield':
                logs.extend(sign_endfield(char, cred, token, d_id))
        logging.info(f"===== 第 {account_index} 个账号处理完成 =====")
    except Exception as e:
        err_msg = f"处理账号 {user_token[:8]}... 时出错: {str(e)}"
        logging.exception(err_msg)
        logs.append(f"❌ {err_msg}")
    return logs


def parse_log_line(log: str):
    """
    解析单行签到日志，返回结构化信息
    格式示例：
      ✅ [明日方舟] 角色 斯卡蒂(B站) 签到成功，获得 合成玉×200 龙门币×10000
      ❌ [终末地] 角色 管理员(官服) 签到失败：重复签到
    """
    pattern = r'^(✅|❌|ℹ️)\s*\[(.+?)\]\s*角色\s+(.+?)\s*\((.+?)\)\s*签到(成功|失败)[：，:]?\s*(.*)$'
    match = re.match(pattern, log)
    if match:
        emoji, game, role, channel, status, extra = match.groups()
        return {
            'emoji': emoji,
            'game': game,
            'role': role,
            'channel': channel,
            'status': status,
            'extra': extra.strip()  # 奖励或失败原因
        }
    # 非角色行（如提示信息）
    return None


def format_push_message(accounts_logs):
    """
    将每个账号的日志列表格式化为美观的推送消息
    :param accounts_logs: list of list，每个元素是一个账号的日志列表
    :return: 格式化后的字符串
    """
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    lines = [f"📋 森空岛签到服务报告", f"执行时间: {current_time}", ""]

    for acc_idx, logs in enumerate(accounts_logs, 1):
        # 解析该账号的所有日志
        game_dict = {}  # 按游戏名分组：{游戏名: [角色信息列表]}
        info_lines = []  # 非角色行（如提示）单独存放
        for log in logs:
            parsed = parse_log_line(log)
            if parsed:
                game = parsed['game']
                if game not in game_dict:
                    game_dict[game] = []
                game_dict[game].append(parsed)
            else:
                # 可能是 ℹ️ 提示，直接添加到info
                info_lines.append(f"  {log}")

        # 如果存在info行，先输出
        if info_lines:
            lines.extend(info_lines)
            lines.append("")

        # 按游戏输出
        for game, roles in game_dict.items():
            lines.append(f"  {game}")
            for role_info in roles:
                emoji = role_info['emoji']
                role = role_info['role']
                channel = role_info['channel']
                status = role_info['status']
                extra = role_info['extra']
                if emoji == '✅':
                    lines.append(f"    📝 签到: ✅ 成功")
                    if extra:
                        lines.append(f"    🎁 奖励: {extra}")
                else:
                    lines.append(f"    📝 签到: ❌ 失败")
                    if extra:
                        lines.append(f"    ℹ️ 原因: {extra}")
            lines.append("")  # 游戏间空行

    return "\n".join(lines).rstrip()



def main():
    if not TOKENS or TOKENS == ['']:
        logging.error("未设置TOKEN环境变量，请设置后运行")
        return

    # 获取设备ID
    try:
        d_id = get_device_id()
    except Exception as e:
        logging.error(f"获取设备ID失败，无法继续: {e}")
        return

    all_accounts_logs = []  # 每个元素是一个账号的日志列表

    for idx, token in enumerate(TOKENS, 1):
        token = token.strip()
        if not token:
            continue
        logs = process_token(token, d_id, idx)
        all_accounts_logs.append(logs)

    # 格式化推送消息
    push_content = format_push_message(all_accounts_logs)

    # 输出到控制台（直接打印美化后的消息，不带时间戳）
    print("\n" + push_content + "\n")

    # 发送通知
    notify_send("森空岛签到报告", push_content)


if __name__ == "__main__":
    main()
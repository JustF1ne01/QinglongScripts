#!/usr/bin/env python3
"""
百度贴吧 每日自动签到脚本
实现功能：
- 获取用户登录状态
- 获取关注的贴吧列表
- 对每个贴吧进行签到
- 统计签到结果
"""

import hashlib
import os
import random
import time
import requests
from typing import Optional, List, Dict, Any

# ==================== 用户配置（从环境变量读取）====================
TIEBA_COOKIE = os.environ.get("TIEBA_COOKIE", "")
# Telegram 推送配置（可选，留空则不推送）
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")
# ===================================================================

# ---------- 日志函数（无颜色，带时间戳和级别）----------
def log_info(msg: str):
    print(f"[INFO] {time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}")

def log_success(msg: str):
    print(f"[SUCCESS] {time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}")

def log_warning(msg: str):
    print(f"[WARNING] {time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}")

def log_error(msg: str):
    print(f"[ERROR] {time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}")

# ---------- 工具函数 ----------
def create_session(cookie: str) -> requests.Session:
    """创建带 Cookie 的 requests Session"""
    session = requests.Session()
    session.headers.update({
        "Host": "tieba.baidu.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36",
        "Connection": "keep-alive",
        "Accept-Encoding": "gzip, deflate",
        "Cache-Control": "no-cache",
    })
    cookie_dict = {item.split("=")[0]: item.split("=")[1] for item in cookie.split("; ") if "=" in item}
    requests.utils.add_dict_to_cookiejar(session.cookies, cookie_dict)
    return session

def encode_data(data: Dict, sign_key: str = "tiebaclient!!!") -> Dict:
    """对请求数据进行签名（原类的 encode_data 方法）"""
    s = ""
    for key in sorted(data.keys()):
        s += f"{key}={data[key]}"
    sign = hashlib.md5((s + sign_key).encode("utf-8")).hexdigest().upper()
    data.update({"sign": sign})
    return data

def request(session: requests.Session, url: str, method: str = "get", data: Optional[Dict] = None, retry: int = 3) -> Dict:
    """带重试的请求函数"""
    for i in range(retry):
        try:
            if method.lower() == "get":
                response = session.get(url, timeout=10)
            else:
                response = session.post(url, data=data, timeout=10)

            response.raise_for_status()
            if not response.text.strip():
                raise ValueError("空响应内容")

            return response.json()

        except Exception as e:
            if i == retry - 1:
                raise Exception(f"请求失败: {e!s}")

            wait_time = 1.5 * (2 ** i) + random.uniform(0, 1)
            time.sleep(wait_time)

    raise Exception(f"请求失败，已达最大重试次数 {retry}")

# ---------- 核心功能函数 ----------
def get_user_info(session: requests.Session, cookie: str) -> tuple:
    """
    获取用户登录信息
    返回 (tbs, user_name) 或 (False, 错误信息)
    """
    tbs_url = "http://tieba.baidu.com/dc/common/tbs"
    try:
        result = request(session, tbs_url)
        if result.get("is_login", 0) == 0:
            return False, "登录失败，Cookie 异常"
        tbs = result.get("tbs", "")
        # 获取用户名（非必须）
        login_info_url = "https://tieba.baidu.com/f/user/json_userinfo"
        try:
            user_info = request(session, login_info_url)
            user_data = user_info.get("data", "")
            if isinstance(user_data, dict):
                user_name = user_data.get("show_nickname", "未知用户")
            else:
                user_name = "未知用户"
        except:
            user_name = "未知用户"
        return tbs, user_name
    except Exception as e:
        return False, f"登录验证异常: {e}"

def get_favorite(session: requests.Session, bduss: str) -> List[Dict]:
    """获取用户关注的贴吧列表"""
    forums = []
    page_no = 1
    like_url = "http://c.tieba.baidu.com/c/f/forum/like"

    while True:
        data = {
            "BDUSS": bduss,
            "_client_type": "2",
            "_client_id": "wappc_1534235498291_488",
            "_client_version": "9.7.8.0",
            "_phone_imei": "000000000000000",
            "from": "1008621y",
            "page_no": str(page_no),
            "page_size": "200",
            "model": "MI+5",
            "net_type": "1",
            "timestamp": str(int(time.time())),
            "vcode_tag": "11",
        }
        data = encode_data(data)

        try:
            res = request(session, like_url, "post", data)

            if "forum_list" in res:
                for forum_type in ["non-gconforum", "gconforum"]:
                    if forum_type in res["forum_list"]:
                        items = res["forum_list"][forum_type]
                        if isinstance(items, list):
                            forums.extend(items)
                        elif isinstance(items, dict):
                            forums.append(items)

            if res.get("has_more") != "1":
                break

            page_no += 1
            time.sleep(random.uniform(1, 2))

        except Exception as e:
            log_error(f"获取贴吧列表出错: {e}")
            break

    log_info(f"共获取到 {len(forums)} 个关注的贴吧")
    return forums

def sign_forums(session: requests.Session, bduss: str, forums: List[Dict], tbs: str) -> Dict[str, Any]:
    """对贴吧列表进行签到，返回统计结果和详细列表"""
    success_count = 0
    error_count = 0
    exist_count = 0
    shield_count = 0
    total = len(forums)
    details = []  # 存储每个贴吧的详细结果

    log_info(f"开始签到 {total} 个贴吧")

    # 签到数据模板
    base_data = {
        "_client_type": "2",
        "_client_version": "9.7.8.0",
        "_phone_imei": "000000000000000",
        "model": "MI+5",
        "net_type": "1",
    }

    last_request_time = time.time()
    for idx, forum in enumerate(forums):
        # 控制请求间隔
        elapsed = time.time() - last_request_time
        delay = max(0, 1.0 + random.uniform(0.5, 1.5) - elapsed)
        time.sleep(delay)
        last_request_time = time.time()

        # 每10个休息长一点
        if (idx + 1) % 10 == 0:
            extra_delay = random.uniform(5, 10)
            log_info(f"已签到 {idx + 1}/{total} 个贴吧，休息 {extra_delay:.2f} 秒")
            time.sleep(extra_delay)

        forum_name = forum.get("name", "")
        forum_id = forum.get("id", "")
        log_prefix = f"【{forum_name}】吧({idx + 1}/{total})"

        try:
            data = base_data.copy()
            data.update({
                "BDUSS": bduss,
                "fid": forum_id,
                "kw": forum_name,
                "tbs": tbs,
                "timestamp": str(int(time.time())),
            })
            data = encode_data(data)

            sign_url = "http://c.tieba.baidu.com/c/c/forum/sign"
            result = request(session, sign_url, "post", data)
            error_code = result.get("error_code", "")
            rank = None

            if error_code == "0":
                success_count += 1
                if "user_info" in result:
                    rank = result["user_info"].get("user_sign_rank")
                    if rank:
                        log_success(f"{log_prefix} 签到成功，第{rank}个签到")
                    else:
                        log_success(f"{log_prefix} 签到成功")
                else:
                    log_success(f"{log_prefix} 签到成功")
                details.append({"name": forum_name, "status": "success", "rank": rank})
            elif error_code == "160002":
                exist_count += 1
                log_warning(f"{log_prefix} {result.get('error_msg', '今日已签到')}")
                details.append({"name": forum_name, "status": "exist", "rank": None})
            elif error_code == "340006":
                shield_count += 1
                log_warning(f"{log_prefix} 贴吧已被屏蔽")
                details.append({"name": forum_name, "status": "shield", "rank": None})
            else:
                error_count += 1
                log_error(f"{log_prefix} 签到失败，错误: {result.get('error_msg', '未知错误')}")
                details.append({"name": forum_name, "status": "error", "rank": None})

        except Exception as e:
            error_count += 1
            log_error(f"{log_prefix} 签到异常: {e!s}")
            details.append({"name": forum_name, "status": "error", "rank": None})

    return {
        "total": total,
        "success": success_count,
        "exist": exist_count,
        "shield": shield_count,
        "error": error_count,
        "details": details,
    }

# ---------- Telegram 推送 ----------
def send_tg_message(text: str):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, data=data, timeout=10)
        if response.status_code != 200:
            log_error(f"Telegram 推送失败: {response.text}")
        else:
            log_success("Telegram 推送成功")
    except Exception as e:
        log_error(f"Telegram 推送异常: {e}")

def build_tg_message(stats: Dict, user_name: str, details: List[Dict]) -> str:
    """构建美观的 Telegram 消息，包含每个贴吧的详细签到结果"""
    lines = []
    lines.append("📢 <b>百度贴吧 签到报告</b>\n")

    # 账号信息
    lines.append(f"👤 <b>账号：</b>{user_name}")

    # 统计摘要
    lines.append("\n📊 <b>签到统计</b>")
    lines.append(f"📌 贴吧总数：{stats['total']}")
    lines.append(f"✅ 签到成功：{stats['success']}")
    lines.append(f"⚠️ 已经签到：{stats['exist']}")
    lines.append(f"🚫 被屏蔽的：{stats['shield']}")
    lines.append(f"❌ 签到失败：{stats['error']}")

    # 详细列表（每个贴吧一行）
    if details:
        lines.append("\n📋 <b>详细签到情况</b>")
        for d in details:
            name = d["name"]
            status = d["status"]
            rank = d.get("rank")

            # 根据状态选择 Emoji
            if status == "success":
                emoji = "✅"
                rank_text = f" (第{rank}个)" if rank else ""
            elif status == "exist":
                emoji = "⚠️"
                rank_text = ""
            elif status == "shield":
                emoji = "🚫"
                rank_text = ""
            else:  # error
                emoji = "❌"
                rank_text = ""

            lines.append(f"{emoji} {name}：{rank_text}")
    else:
        lines.append("\n📋 无详细签到记录")

    lines.append("\n———————————————")
    lines.append(f"🕒 执行时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")

    return "\n".join(lines)

# ---------- 主函数 ----------
def main() -> Dict:
    """主流程，返回包含统计、用户名和详细结果的字典"""
    # 从 Cookie 中提取 BDUSS
    cookie_dict = {item.split("=")[0]: item.split("=")[1] for item in TIEBA_COOKIE.split("; ") if "=" in item}
    bduss = cookie_dict.get("BDUSS", "")
    if not bduss:
        log_error("Cookie 中未找到 BDUSS，请检查配置")
        return {"user_name": "未知", "stats": {"total": 0, "success": 0, "exist": 0, "shield": 0, "error": 0}, "details": []}

    session = create_session(TIEBA_COOKIE)

    # 获取用户信息
    tbs, user_name = get_user_info(session, TIEBA_COOKIE)
    if not tbs:
        log_error(user_name)  # user_name 此时是错误信息
        return {"user_name": "登录失败", "stats": {"total": 0, "success": 0, "exist": 0, "shield": 0, "error": 0}, "details": []}

    log_success(f"登录成功，用户名：{user_name}")

    # 获取关注的贴吧列表
    forums = get_favorite(session, bduss=bduss)
    if not forums:
        log_warning("未获取到任何贴吧，请检查 Cookie 或网络")
        return {"user_name": user_name, "stats": {"total": 0, "success": 0, "exist": 0, "shield": 0, "error": 0}, "details": []}

    # 执行签到
    result = sign_forums(session, bduss, forums, tbs)

    # 输出统计
    log_info(f"签到完成：总数 {result['total']}，成功 {result['success']}，已签 {result['exist']}，屏蔽 {result['shield']}，失败 {result['error']}")

    return {"user_name": user_name, "stats": result, "details": result["details"]}

if __name__ == "__main__":
    result = main()
    if result:
        tg_text = build_tg_message(result["stats"], result["user_name"], result["details"])
        send_tg_message(tg_text)
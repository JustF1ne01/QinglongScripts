#!/usr/bin/env python3
"""
阿里云盘 每日签到脚本
实现功能：
- 刷新 Access Token
- 执行签到
- 获取累计签到天数和奖励信息
"""

import json
import os
import time
import requests
import urllib3
from typing import Optional, Dict, Any

urllib3.disable_warnings()

# ==================== 用户配置（从环境变量读取）====================
ALIYUN_REFRESH_TOKEN = os.environ.get("ALIYUN_REFRESH_TOKEN", "")
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

# ---------- 核心功能函数 ----------
def update_token(refresh_token: str) -> Optional[str]:
    """使用 refresh_token 获取新的 access_token"""
    url = "https://auth.aliyundrive.com/v2/account/token"
    data = {"grant_type": "refresh_token", "refresh_token": refresh_token}
    try:
        response = requests.post(url=url, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        access_token = result.get("access_token")
        if access_token:
            log_success("Token 刷新成功")
            return access_token
        else:
            log_error("Token 刷新失败，响应中无 access_token")
            return None
    except Exception as e:
        log_error(f"Token 刷新异常: {e}")
        return None

def sign(access_token: str) -> Dict[str, Any]:
    """执行签到，返回累计天数和奖励信息"""
    url = "https://member.aliyundrive.com/v1/activity/sign_in_list"
    headers = {
        "Authorization": access_token,
        "Content-Type": "application/json"
    }
    try:
        # 获取签到列表
        result = requests.post(url=url, headers=headers, json={}, timeout=10).json()
        if "success" not in result or not result["success"]:
            log_error(f"签到失败：{result.get('message', '未知错误')}")
            return {"success": False, "message": result.get('message', '未知错误')}

        sign_days = result["result"]["signInCount"]
        log_info(f"累计签到天数：{sign_days}")

        # 获取奖励（实际上签到奖励是自动发放的，但官方接口需要再调用一次 reward）
        reward_name = ""
        reward_desc = ""
        # 查找第一个未领取奖励的签到日？原脚本逻辑是取最后一个已签到的奖励，但更合理的是直接获取今日奖励
        # 简化：从签到列表中找今日的奖励（如果今日已签到）
        today_log = None
        for log in result["result"]["signInLogs"]:
            if log["status"] == "normal":  # 假设今日已签到的状态是 normal
                today_log = log
                break
        if today_log and today_log.get("reward"):
            reward_name = today_log["reward"].get("name", "")
            reward_desc = today_log["reward"].get("description", "")
            log_success(f"今日奖励：{reward_name}{reward_desc}")
        else:
            log_warning("今日奖励信息未找到或尚未获得奖励")

        return {
            "success": True,
            "sign_days": sign_days,
            "reward_name": reward_name,
            "reward_desc": reward_desc
        }
    except Exception as e:
        log_error(f"签到请求异常: {e}")
        return {"success": False, "message": str(e)}

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

def build_tg_message(result: Dict[str, Any], refresh_token: str) -> str:
    """构建美观的 Telegram 消息"""
    lines = []
    lines.append("📦 <b>阿里云盘 签到报告</b>\n")

    if result.get("success"):
        lines.append(f"\n✅ <b>签到状态：</b>成功")
        lines.append(f"📅 <b>累计签到：</b>{result['sign_days']} 天")
        if result['reward_name'] or result['reward_desc']:
            lines.append(f"🎁 <b>今日奖励：</b>{result['reward_name']}{result['reward_desc']}")
        else:
            lines.append(f"🎁 <b>今日奖励：</b>无")
    else:
        lines.append(f"\n❌ <b>签到状态：</b>失败")
        lines.append(f"⚠️ <b>错误信息：</b>{result.get('message', '未知错误')}")

    lines.append("\n———————————————")
    lines.append(f"🕒 <b>执行时间：</b>{time.strftime('%Y-%m-%d %H:%M:%S')}")

    return "\n".join(lines)

# ---------- 主函数 ----------
def main() -> Dict[str, Any]:
    """主流程，返回签到结果字典"""
    if not ALIYUN_REFRESH_TOKEN:
        log_error("未配置 ALIYUN_REFRESH_TOKEN")
        return {"success": False, "message": "未配置 refresh_token"}

    # 刷新 token
    access_token = update_token(ALIYUN_REFRESH_TOKEN)
    if not access_token:
        return {"success": False, "message": "Token 刷新失败"}

    # 执行签到
    result = sign(access_token)
    return result

if __name__ == "__main__":
    result = main()
    tg_text = build_tg_message(result, ALIYUN_REFRESH_TOKEN)
    send_tg_message(tg_text)
    # 控制台输出最终结果
    log_info(f"签到结果：{result}")
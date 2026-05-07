#!/usr/bin/env python3
# new Env('Bitwarden备份')
# cron: 0 0 * * *
"""
Bitwarden自动备份脚本（带哈希比较，避免重复同步）

功能：
1. 自动登录Bitwarden服务器并获取所有密码数据
2. 将密码数据保存到本地JSON文件
3. 比较今天与昨天的备份文件哈希，若无变化则跳过WebDAV同步
4. 将备份文件同步到WebDAV服务器（仅当有更新时）
5. 通过notify模块发送备份报告

作者：自动生成
版本：1.1.0
"""

# 导入外部库
import os
import json
import logging
import requests
from notify import send as notify_send
import datetime
import hashlib
from requests.auth import HTTPBasicAuth
from typing import Dict, Any, Tuple

# ========== 用户配置区域（从环境变量读取） ==========
# Bitwarden配置
BITWARDEN_SERVER = os.environ.get("BITWARDEN_SERVER", "")
BITWARDEN_USERNAME = os.environ.get("BITWARDEN_USERNAME", "")
BITWARDEN_PASSWORD = os.environ.get("BITWARDEN_PASSWORD", "")

# WebDAV配置
WEBDAV_SERVER = os.environ.get("WEBDAV_SERVER", "")
WEBDAV_USERNAME = os.environ.get("WEBDAV_USERNAME", "")
WEBDAV_PASSWORD = os.environ.get("WEBDAV_PASSWORD", "")
WEBDAV_REMOTE_DIR = os.environ.get("WEBDAV_REMOTE_DIR", "")

# 本地路径配置
LOCAL_BACKUP_PATH = os.environ.get("SYNC_LOCAL_DIR", "")

# 备份配置
BACKUP_FILENAME_FORMAT = "%Y-%m-%d_bitwarden_backup.json"  # 使用日期作为文件名

# ========== 日志配置 ==========
def setup_logging():
    """配置日志系统"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ========== 功能函数区域 ==========
def create_session() -> requests.Session:
    """创建并配置一个requests会话"""
    session = requests.Session()
    # 设置默认请求头
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
    })
    return session

def bitwarden_login(session: requests.Session) -> Tuple[bool, str]:
    """
    登录Bitwarden服务器
    
    Args:
        session: requests会话对象
        
    Returns:
        tuple: (登录是否成功, 日志消息)
    """
    login_url = f"{BITWARDEN_SERVER.rstrip('/')}/identity/connect/token"
    
    login_data = {
        "scope": "api offline_access",
        "client_id": "web",
        "deviceType": "12",
        "deviceIdentifier": "65ff3d73-fd5f-4835-8a50-fa7f41581f48",
        "deviceName": "edge",
        "grant_type": "password",
        "username": BITWARDEN_USERNAME,
        "password": BITWARDEN_PASSWORD,
    }
    
    try:
        logger.info(f"正在登录Bitwarden服务器: {BITWARDEN_SERVER}")
        response = session.post(login_url, data=login_data, timeout=30)
        response.raise_for_status()
        
        # 解析响应
        json_response = response.json()
        access_token = json_response.get("access_token")
        
        if access_token:
            # 更新会话头信息
            session.headers.update({"Authorization": f"Bearer {access_token}"})
            logger.info("Bitwarden登录成功")
            return True, "✅ Bitwarden登录成功"
        else:
            logger.error(f"登录响应中未找到access_token: {json_response}")
            return False, "❌ Bitwarden登录失败: 响应中未找到access_token"
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Bitwarden登录请求失败: {e}")
        return False, f"❌ Bitwarden登录失败: 网络请求错误 - {e}"
    except json.JSONDecodeError as e:
        logger.error(f"解析登录响应JSON失败: {e}")
        return False, f"❌ Bitwarden登录失败: 响应格式错误 - {e}"
    except Exception as e:
        logger.error(f"Bitwarden登录过程中发生未知错误: {e}")
        return False, f"❌ Bitwarden登录失败: 未知错误 - {e}"

def get_bitwarden_data(session: requests.Session) -> Tuple[bool, Any, str]:
    """
    从Bitwarden获取密码数据
    
    Args:
        session: 已登录的requests会话对象
        
    Returns:
        tuple: (是否成功, 密码数据, 日志消息)
    """
    sync_url = f"{BITWARDEN_SERVER.rstrip('/')}/api/sync"
    
    try:
        logger.info("正在从Bitwarden获取密码数据...")
        response = session.get(sync_url, params={"excludeDomains": "true"}, timeout=30)
        response.raise_for_status()
        
        # 解析响应数据
        data = response.json()
        
        # 检查数据是否有效
        if data and isinstance(data, dict):
            item_count = len(data.get("ciphers", []))
            logger.info(f"成功获取Bitwarden数据，包含{item_count}个密码项")
            return True, data, f"✅ 成功获取Bitwarden数据 ({item_count}个密码项)"
        else:
            logger.warning("获取到的Bitwarden数据为空或格式不正确")
            return False, None, "⚠️ 获取Bitwarden数据: 数据为空或格式不正确"
            
    except requests.exceptions.RequestException as e:
        logger.error(f"获取Bitwarden数据请求失败: {e}")
        return False, None, f"❌ 获取Bitwarden数据失败: 网络请求错误 - {e}"
    except json.JSONDecodeError as e:
        logger.error(f"解析Bitwarden数据JSON失败: {e}")
        return False, None, f"❌ 获取Bitwarden数据失败: 响应格式错误 - {e}"
    except Exception as e:
        logger.error(f"获取Bitwarden数据过程中发生未知错误: {e}")
        return False, None, f"❌ 获取Bitwarden数据失败: 未知错误 - {e}"

def save_backup_locally(data: Dict[str, Any]) -> Tuple[bool, str, str]:
    """
    将备份数据保存到本地文件
    
    Args:
        data: 要保存的Bitwarden数据
        
    Returns:
        tuple: (是否成功, 文件路径, 日志消息)
    """
    # 确保备份目录存在
    if not os.path.exists(LOCAL_BACKUP_PATH):
        try:
            os.makedirs(LOCAL_BACKUP_PATH, exist_ok=True)
            logger.info(f"创建备份目录: {LOCAL_BACKUP_PATH}")
        except Exception as e:
            logger.error(f"创建备份目录失败: {e}")
            return False, "", f"❌ 创建备份目录失败: {e}"
    
    # 生成文件名
    today = datetime.datetime.now()
    filename = today.strftime(BACKUP_FILENAME_FORMAT)
    filepath = os.path.join(LOCAL_BACKUP_PATH, filename)
    
    try:
        # 保存数据到文件
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        # 获取文件大小
        file_size = os.path.getsize(filepath)
        file_size_mb = file_size / (1024 * 1024)
        
        logger.info(f"备份数据已保存到: {filepath} ({file_size_mb:.2f} MB)")
        return True, filepath, f"✅ 本地备份成功: `{filename}` ({file_size_mb:.2f} MB)"
        
    except Exception as e:
        logger.error(f"保存备份文件失败: {e}")
        return False, "", f"❌ 本地备份失败: {e}"

def get_file_hash(filepath: str) -> str:
    """
    计算文件的MD5哈希值
    
    Args:
        filepath: 文件路径
        
    Returns:
        str: 哈希值的十六进制字符串
    """
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def sync_to_webdav(local_filepath: str) -> Tuple[bool, str]:
    """
    将本地备份文件同步到WebDAV服务器
    
    Args:
        local_filepath: 本地备份文件路径
        
    Returns:
        tuple: (是否成功, 日志消息)
    """
    if not os.path.exists(local_filepath):
        logger.error(f"本地文件不存在: {local_filepath}")
        return False, f"❌ WebDAV同步失败: 本地文件不存在"
    
    # 构建远程路径
    filename = os.path.basename(local_filepath)
    remote_dir = WEBDAV_REMOTE_DIR.strip('/')
    remote_path = f"{WEBDAV_SERVER.rstrip('/')}/{remote_dir}/{filename}"
    
    try:
        # 读取文件内容
        with open(local_filepath, 'rb') as f:
            file_data = f.read()
        
        # 上传到WebDAV
        logger.info(f"正在上传到WebDAV: {remote_path}")
        response = requests.put(
            url=remote_path,
            data=file_data,
            auth=HTTPBasicAuth(WEBDAV_USERNAME, WEBDAV_PASSWORD),
            headers={'Content-Type': 'application/octet-stream'},
            timeout=60
        )
        
        if response.status_code in (200, 201, 204):
            logger.info(f"WebDAV同步成功: {local_filepath} -> {remote_path}")
            return True, f"✅ WebDAV同步成功: `{filename}`"
        else:
            logger.error(f"WebDAV同步失败，状态码: {response.status_code}, 响应: {response.text}")
            return False, f"❌ WebDAV同步失败: 服务器返回状态码 {response.status_code}"
            
    except requests.exceptions.RequestException as e:
        logger.error(f"WebDAV同步请求失败: {e}")
        return False, f"❌ WebDAV同步失败: 网络请求错误 - {e}"
    except Exception as e:
        logger.error(f"WebDAV同步过程中发生未知错误: {e}")
        return False, f"❌ WebDAV同步失败: 未知错误 - {e}"

def build_report(log_messages: list) -> str:
    """构建备份报告"""
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report_lines = [
        f"📅 备份时间: {current_time}",
        f"👤 账户: {BITWARDEN_USERNAME}",
        "",
        "📋 备份步骤状态:",
    ]

    for i, log_msg in enumerate(log_messages, 1):
        emoji = '•'
        clean_msg = log_msg
        for e in ['✅', '❌', '⚠️', 'ℹ️', '⏭️']:
            if log_msg.startswith(e):
                emoji = e
                clean_msg = log_msg[len(e):].strip()
                break
        report_lines.append(f"  {i}. {emoji} {clean_msg}")

    success_count = sum(1 for msg in log_messages if msg.startswith("✅"))
    info_count = sum(1 for msg in log_messages if msg.startswith("ℹ️"))
    skip_count = sum(1 for msg in log_messages if msg.startswith("⏭️"))
    total_count = len(log_messages)

    report_lines.extend([
        "",
        "📊 统计信息:",
        f"  成功: {success_count} | 信息: {info_count} | 跳过: {skip_count} | 总计: {total_count}",
        "",
        f"自动备份脚本 • {datetime.datetime.now().strftime('%Y-%m-%d')}"
    ])

    return "\n".join(report_lines)

def perform_backup() -> Tuple[bool, list, str, bool]:
    """
    执行完整的备份流程
    
    Returns:
        tuple: (是否完全成功, 日志消息列表, 备份文件路径, 是否有更新)
    """
    log_messages = []
    backup_filepath = None
    has_update = True  # 默认有更新

    try:
        # 1. 创建会话
        session = create_session()
        
        # 2. 登录Bitwarden
        login_success, login_msg = bitwarden_login(session)
        log_messages.append(login_msg)
        
        if not login_success:
            logger.error("Bitwarden登录失败，备份流程终止")
            return False, log_messages, None, has_update
        
        # 3. 获取Bitwarden数据
        data_success, bitwarden_data, data_msg = get_bitwarden_data(session)
        log_messages.append(data_msg)
        
        if not data_success or bitwarden_data is None:
            logger.error("获取Bitwarden数据失败，备份流程终止")
            return False, log_messages, None, has_update
        
        # 4. 保存到本地
        save_success, filepath, save_msg = save_backup_locally(bitwarden_data)
        log_messages.append(save_msg)
        backup_filepath = filepath if save_success else None
        
        # 5. 检查是否有更新（与昨天的文件比较）
        if save_success and backup_filepath:
            today = datetime.datetime.now()
            yesterday = today - datetime.timedelta(days=1)
            yesterday_filename = yesterday.strftime(BACKUP_FILENAME_FORMAT)
            yesterday_filepath = os.path.join(LOCAL_BACKUP_PATH, yesterday_filename)
            
            if os.path.exists(yesterday_filepath):
                new_hash = get_file_hash(backup_filepath)
                old_hash = get_file_hash(yesterday_filepath)
                if new_hash == old_hash:
                    has_update = False
                    logger.info("备份文件与昨天内容相同，无更新")
                    log_messages.append("ℹ️ 备份文件与昨日一致，无新内容")
                else:
                    logger.info("备份文件有更新")
            else:
                logger.info("昨日备份文件不存在，视为有更新")
            
            # 6. 同步到WebDAV（仅当有更新时）
            if has_update:
                sync_success, sync_msg = sync_to_webdav(backup_filepath)
                log_messages.append(sync_msg)
            else:
                log_messages.append("⏭️ WebDAV同步跳过: 文件无变化")
        else:
            log_messages.append("⏭️ WebDAV同步跳过: 本地备份失败")
        
        # 检查整体是否成功
        all_success = all(
            msg.startswith("✅") or msg.startswith("⏭️") or msg.startswith("ℹ️") 
            for msg in log_messages
        )
        
        return all_success, log_messages, backup_filepath, has_update
        
    except Exception as e:
        logger.error(f"备份流程执行过程中发生未捕获的异常: {e}")
        log_messages.append(f"❌ 备份流程异常: {str(e)[:100]}")
        return False, log_messages, backup_filepath, has_update

# ========== 主函数 ==========
def main():
    """
    主函数 - 程序入口点
    """
    logger.info("=" * 50)
    logger.info("Bitwarden自动备份脚本开始执行")
    logger.info("=" * 50)
    
    # 检查必填环境变量
    missing = []
    for var in ("WEBDAV_REMOTE_DIR", "SYNC_LOCAL_DIR"):
        if not os.environ.get(var):
            missing.append(var)
    if missing:
        msg = f"❌ 缺少必填环境变量: {', '.join(missing)}，请在环境变量中配置后重试"
        logger.error(msg)
        notify_send("Bitwarden备份失败", msg)
        return 1
    
    # 记录开始时间
    start_time = datetime.datetime.now()
    
    try:
        # 执行备份流程
        backup_success, log_messages, backup_filepath, has_update = perform_backup()
        
        # 发送报告
        report = build_report(log_messages)
        notify_send("Bitwarden备份报告", report)
        
        # 在控制台显示报告摘要
        print("\n" + "=" * 60)
        print("Bitwarden备份完成报告:")
        print("=" * 60)
        
        for i, msg in enumerate(log_messages, 1):
            print(f"{i}. {msg}")
        
        # 显示统计信息
        success_count = sum(1 for msg in log_messages if msg.startswith("✅"))
        info_count = sum(1 for msg in log_messages if msg.startswith("ℹ️"))
        skip_count = sum(1 for msg in log_messages if msg.startswith("⏭️"))
        total_count = len(log_messages)
        
        print("\n" + "-" * 40)
        print(f"总结: {success_count}个成功, {info_count}个信息, {skip_count}个跳过, 总计{total_count}个步骤")
        print(f"备份文件: {backup_filepath or '未生成'}")
        print(f"文件更新: {'是' if has_update else '否（无变化）'}")
        
        # 计算执行时间
        end_time = datetime.datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        print(f"执行时间: {execution_time:.2f}秒")
        print("=" * 60)
        
        # 根据备份结果返回退出代码
        if backup_success:
            logger.info("备份流程完全成功")
            return 0
        else:
            logger.warning("备份流程部分失败")
            return 1
            
    except KeyboardInterrupt:
        logger.info("用户中断执行")
        return 130
    except Exception as e:
        logger.error(f"脚本执行过程中发生未捕获的异常: {e}")
        notify_send("Bitwarden备份异常", f"错误: {str(e)[:200]}")
        return 1

# ========== 程序入口 ==========
if __name__ == "__main__":
    import sys
    
    # 设置退出代码
    exit_code = main()
    
    # 记录结束信息
    logger.info("=" * 50)
    logger.info(f"脚本执行结束，退出代码: {exit_code}")
    logger.info("=" * 50)
    
    # 退出程序
    sys.exit(exit_code)
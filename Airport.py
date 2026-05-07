#!/usr/bin/env python3
# new Env('机场签到')
# cron: 0 0 * * *
"""
多服务自动签到脚本

功能：
1. 自动登录多个指定服务网站
2. 执行每日签到任务
3. 获取剩余流量信息
4. 发送格式化通知（通过notify模块）

作者：自动生成
版本：2.0.0
"""

# 导入外部库
import os
import re
import sys
import time
import base64
import logging
import requests
from datetime import datetime
from lxml import html
from typing import Dict, Any, List, Tuple
from notify import send as notify_send

# ========== 用户配置区域（从环境变量读取） ==========
# ========== 服务配置列表 ==========
# 每个服务是一个字典，包含以下字段：
#   name          : 服务显示名称
#   base_url      : 服务基础URL
#   login_path    : 登录路径
#   checkin_path  : 签到路径
#   user_info_path: 用户信息页面路径
#   traffic_xpath : 提取流量信息的XPath
#   username      : 登录用户名/邮箱（从环境变量读取）
#   password      : 登录密码（从环境变量读取）
SERVICES = [
    {
        "name": "速鹰666",
        "base_url": "https://suying00.com",
        "login_path": "/auth/login",
        "checkin_path": "/user/checkin",
        "user_info_path": "/user",
        "traffic_xpath": '//*[@id="app"]/div/div[3]/section/div[3]/div[2]/div/div[2]/div[2]',
        "username": os.environ.get("SUYING_USERNAME", ""),
        "password": os.environ.get("SUYING_PASSWORD", "")
    },
    {
        "name": "iKuuu",
        "base_url": "https://ikuuu.org",
        "login_path": "/auth/login",
        "checkin_path": "/user/checkin",
        "user_info_path": "/user",
        "traffic_xpath": "//h4[contains(text(),'剩余流量')]/ancestor::div[contains(@class,'card')]//div[contains(@class,'card-body')]",
        "username": os.environ.get("IKUUU_USERNAME", ""),
        "password": os.environ.get("IKUUU_PASSWORD", "")
    },
    {
        "name": "69yun",
        "base_url": "https://69yun69.com",
        "login_path": "/auth/login",
        "checkin_path": "/user/checkin",
        "user_info_path": "/user",
        "traffic_xpath": "//*[@id='kt_content']/div[2]/div/div[2]/div[2]/div/div[1]/div/div/div",
        "username": os.environ.get("YUN69_USERNAME", ""),
        "password": os.environ.get("YUN69_PASSWORD", "")
    },
]

# 其他配置
LOG_LEVEL = logging.INFO
REQUEST_TIMEOUT = 10

# ========== 日志配置 ==========
def setup_logging():
    """配置日志系统"""
    logging.basicConfig(
        level=LOG_LEVEL,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ========== 功能函数区域 ==========
def create_session():
    """创建并配置一个requests会话"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    })
    return session

def login_to_service(service_config: Dict[str, str]) -> Tuple[bool, Any]:
    """
    登录到服务网站

    Args:
        service_config: 服务配置字典

    Returns:
        tuple: (登录是否成功, session对象或错误信息)
    """
    session = create_session()
    login_url = f"{service_config['base_url']}{service_config['login_path']}"
    username = service_config['username']
    password = service_config['password']

    # 构建登录数据
    login_data = {
        "email": username,
        "passwd": password,
        "remember_me": "on",
        "code": ""  # 如果有验证码需要填写
    }

    try:
        logger.info(f"正在登录 [{service_config['name']}] 账户: {username}")
        response = session.post(login_url, data=login_data, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        # 判断登录是否成功
        login_success = False

        # 方法1: 检查返回的JSON
        try:
            json_data = response.json()
            if json_data.get('ret') == 1 or json_data.get('success'):
                login_success = True
                logger.info(f"[{service_config['name']}] 登录成功 (通过JSON返回状态判断)")
        except:
            pass

        # 方法2: 检查cookie
        if not login_success:
            cookies = session.cookies.get_dict()
            if 'uid' in cookies or 'key' in cookies or 'email' in cookies:
                login_success = True
                logger.info(f"[{service_config['name']}] 登录成功 (通过Cookie判断)")

        # 方法3: 检查响应文本
        if not login_success and response.text:
            success_keywords = ['登录成功', 'login success', 'success', '欢迎']
            if any(keyword in response.text.lower() for keyword in [k.lower() for k in success_keywords]):
                login_success = True
                logger.info(f"[{service_config['name']}] 登录成功 (通过响应文本判断)")

        if login_success:
            return True, session
        else:
            logger.error(f"[{service_config['name']}] 登录失败，响应内容: {response.text[:200]}")
            return False, "无法判断登录状态，请检查账号密码或网站状态"

    except requests.exceptions.RequestException as e:
        logger.error(f"[{service_config['name']}] 登录请求失败: {e}")
        return False, f"网络请求失败: {e}"
    except Exception as e:
        logger.error(f"[{service_config['name']}] 登录过程中发生未知错误: {e}")
        return False, f"未知错误: {e}"

def perform_checkin(session, service_config: Dict[str, str]) -> Dict[str, Any]:
    """
    执行签到操作
    """
    checkin_url = f"{service_config['base_url']}{service_config['checkin_path']}"
    result = {
        "success": False,
        "message": "签到失败",
        "details": {}
    }

    try:
        logger.info(f"[{service_config['name']}] 正在执行签到...")
        response = session.post(checkin_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        # 尝试解析JSON响应
        try:
            json_data = response.json()
            # --- 新增：对69云的特殊处理，去除多余广告信息 ---
            if service_config['name'] == '69yun' and 'msg' in json_data:
                # 仅保留第一行（通常是“您似乎已经签到过了...”），并去除首尾空格
                json_data['msg'] = json_data['msg'].split('\n')[0].strip()
            # --------------------------------------------
            result["details"] = json_data
            result["message"] = json_data.get("msg", "签到完成")
            result["success"] = True
            logger.info(f"[{service_config['name']}] 签到成功: {result['message']}")
        except ValueError:
            # 如果不是JSON格式，记录文本内容
            result["message"] = "签到完成，但返回非标准格式"
            result["details"] = {"raw_response": response.text[:500]}
            result["success"] = True
            logger.info(f"[{service_config['name']}] 签到完成，返回文本: {response.text[:200]}")

    except requests.exceptions.RequestException as e:
        logger.error(f"[{service_config['name']}] 签到请求失败: {e}")
        result["message"] = f"网络请求失败: {e}"
    except Exception as e:
        logger.error(f"[{service_config['name']}] 签到过程中发生未知错误: {e}")
        result["message"] = f"未知错误: {e}"

    return result

def extract_and_decode_base64(html_content):
    """从 HTML 中提取 originBody 的 base64 内容并解码"""
    # 匹配 var originBody = "base64_string";  (支持单双引号)
    pattern = r'var\s+originBody\s*=\s*["\']([^"\']+)["\']'
    match = re.search(pattern, html_content)
    if match:
        base64_str = match.group(1)
        try:
            decoded_bytes = base64.b64decode(base64_str)
            decoded_html = decoded_bytes.decode('utf-8')
            return decoded_html
        except Exception as e:
            logger.warning(f"Base64 解码失败: {e}")
            return None
    return None

def get_traffic_info(session, service_config: Dict[str, str]) -> Dict[str, Any]:
    """
    获取剩余流量信息
    """
    info_url = f"{service_config['base_url']}{service_config['user_info_path']}"
    result = {
        "success": False,
        "traffic": "获取失败",
        "raw_html": None,
        "error": None
    }

    try:
        logger.info(f"[{service_config['name']}] 正在获取流量信息...")
        response = session.get(info_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        # 保存原始HTML用于调试
        raw_html = response.text
        result["raw_html"] = raw_html

        # 针对 iKuuu 等可能包含 base64 编码的站点进行解码
        decoded_html = extract_and_decode_base64(raw_html)
        if decoded_html:
            logger.info(f"[{service_config['name']}] 检测到 base64 编码内容，解码成功")
            html_to_parse = decoded_html
        else:
            html_to_parse = raw_html

        # 使用 XPath 提取流量信息
        tree = html.fromstring(html_to_parse)
        traffic_elements = tree.xpath(service_config['traffic_xpath'])

        if traffic_elements:
            traffic_text = traffic_elements[0].text_content().strip()
            result["traffic"] = traffic_text
            result["success"] = True
            logger.info(f"[{service_config['name']}] 成功获取流量信息: {traffic_text}")
        else:
            result["error"] = "XPath未找到匹配元素，页面结构可能已变更"
            logger.warning(f"[{service_config['name']}] {result['error']}")

            # 尝试寻找其他可能的流量信息（仅在未解码时执行）
            if not decoded_html:
                logger.info(f"[{service_config['name']}] 尝试查找其他可能的流量信息...")
                all_text_elements = tree.xpath('//*[contains(text(), "流量") or contains(text(), "traffic")]')
                if all_text_elements:
                    logger.info(f"[{service_config['name']}] 找到{len(all_text_elements)}个包含流量关键词的元素")
                    for elem in all_text_elements[:5]:
                        text = elem.text_content().strip()
                        if text and len(text) < 100:
                            logger.info(f"  可能: {text}")

    except requests.exceptions.RequestException as e:
        logger.error(f"[{service_config['name']}] 获取流量信息请求失败: {e}")
        result["error"] = f"网络请求失败: {e}"
    except Exception as e:
        logger.error(f"[{service_config['name']}] 解析流量信息时发生未知错误: {e}")
        result["error"] = f"解析错误: {e}"

    return result

def format_multi_checkin_report(results: List[Dict[str, Any]]) -> str:
    """
    格式化多个服务的签到报告

    Args:
        results: 每个服务的结果列表，每个结果包含：
                 'name': 服务名称
                 'checkin_result': 签到结果字典
                 'traffic_result': 流量结果字典
                 'login_error': 登录错误信息（如果有）

    Returns:
        str: 格式化后的报告
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "📋 多服务签到报告",
        f"执行时间: {current_time}",
        ""
    ]

    for idx, res in enumerate(results, 1):
        name = res['name']
        checkin = res['checkin_result']
        traffic = res['traffic_result']
        login_error = res.get('login_error')

        lines.append(f"{idx}. {name}")

        # 登录状态
        if login_error:
            lines.append(f"  🔐 登录: ❌ 失败")
            lines.append(f"     错误: {login_error}")
            lines.append(f"  📝 签到: 跳过")
            lines.append(f"  📊 流量: 跳过")
        else:
            # 签到状态
            if checkin['success']:
                lines.append(f"  📝 签到: ✅ 成功")
                lines.append(f"     消息: {checkin['message']}")
            else:
                lines.append(f"  📝 签到: ❌ 失败")
                lines.append(f"     消息: {checkin['message']}")

            # 流量状态
            if traffic['success']:
                lines.append(f"  📊 流量: ✅ 剩余 {traffic['traffic']}")
            else:
                lines.append(f"  📊 流量: ❌ 获取失败")
                if traffic.get('error'):
                    lines.append(f"     错误: {traffic['error']}")

        lines.append("")  # 空行分隔

    lines.extend([
        "---",
        f"自动签到脚本 • {datetime.now().strftime('%Y-%m-%d')}"
    ])

    return "\n".join(lines)

def save_debug_info(service_name, traffic_result, checkin_result):
    """
    保存调试信息到文件

    Args:
        service_name: 服务名称
        traffic_result: 流量结果字典
        checkin_result: 签到结果字典
    """
    if traffic_result.get("raw_html"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"debug_{service_name}_{timestamp}.html"

        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write("=== 调试信息 ===\n")
                f.write(f"服务: {service_name}\n")
                f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"签到结果: {checkin_result}\n")
                f.write(f"流量结果: {traffic_result.get('traffic', 'N/A')}\n")
                f.write(f"错误信息: {traffic_result.get('error', '无')}\n")
                f.write("\n=== 原始HTML ===\n")
                f.write(traffic_result["raw_html"])

            logger.info(f"调试信息已保存到: {filename}")
            return filename
        except Exception as e:
            logger.error(f"保存调试信息失败: {e}")

    return None

# ========== 主函数 ==========
def main():
    """
    主函数 - 程序入口点
    """
    logger.info("=" * 50)
    logger.info("多服务自动签到脚本开始执行")
    logger.info("=" * 50)

    # 记录开始时间
    start_time = time.time()

    try:
        results = []  # 收集所有服务的结果

        # 遍历每个服务
        for service in SERVICES:
            service_name = service['name']
            logger.info(f"--- 开始处理服务: {service_name} ---")

            # 1. 登录服务
            login_success, login_result = login_to_service(service)

            if not login_success:
                # 登录失败，记录错误并跳过该服务
                logger.error(f"[{service_name}] 登录失败: {login_result}")
                results.append({
                    "name": service_name,
                    "login_error": login_result,
                    "checkin_result": None,
                    "traffic_result": None
                })
                continue

            session = login_result
            logger.info(f"[{service_name}] 登录成功，继续执行签到流程")

            # 2. 执行签到
            checkin_result = perform_checkin(session, service)

            # 3. 获取流量信息
            traffic_result = get_traffic_info(session, service)

            # 保存结果
            results.append({
                "name": service_name,
                "login_error": None,
                "checkin_result": checkin_result,
                "traffic_result": traffic_result
            })

            # 如果需要，保存调试信息（流量获取失败时）
            if not traffic_result["success"] and traffic_result.get("raw_html"):
                save_debug_info(service_name, traffic_result, checkin_result)

            logger.info(f"--- 服务 {service_name} 处理完成 ---")

        # 4. 格式化合并报告
        report = format_multi_checkin_report(results)

        # 5. 发送报告
        notify_send("机场签到报告", report)

        # 6. 在控制台显示报告
        print("\n" + "=" * 60)
        print(report)
        print("=" * 60)

        # 7. 计算执行时间
        execution_time = time.time() - start_time
        logger.info(f"脚本执行完成，耗时: {execution_time:.2f}秒")

        # 返回整体成功状态（只要有一个服务签到成功就算成功？可根据需求调整）
        any_success = any(
            res.get('checkin_result') and res['checkin_result']['success']
            for res in results
        )
        return 0 if any_success else 1

    except KeyboardInterrupt:
        logger.info("用户中断执行")
        return 130
    except Exception as e:
        logger.error(f"脚本执行过程中发生未捕获的异常: {e}")
        notify_send("机场签到异常", str(e)[:200])
        return 1

# ========== 程序入口 ==========
if __name__ == "__main__":
    # 设置退出代码
    exit_code = main()

    # 记录结束信息
    logger.info("=" * 50)
    logger.info(f"脚本执行结束，退出代码: {exit_code}")
    logger.info("=" * 50)

    # 退出程序
    sys.exit(exit_code)
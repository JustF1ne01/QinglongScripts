#!/usr/bin/env python3
# new Env('SSL证书检查')
# cron: 0 0 * * *
"""
SSL证书检查脚本

功能：
1. 批量检查多个域名的SSL证书状态
2. 获取证书到期时间、剩余天数、颁发者等信息
3. 发送格式化报告到Telegram
4. 分类显示正常、警告、过期和检查失败的证书

作者：自动生成
版本：1.0.0
"""

# 导入外部库
import os
import ssl
import socket
import logging
import requests
from notify import send as notify_send
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# ========== 用户配置区域（从环境变量读取） ==========
# 要检查的域名列表（环境变量中用英文逗号分隔，如 "a.com,b.com,c.com:8443"）
DOMAINS_TO_CHECK = [d.strip() for d in os.environ.get("SSL_DOMAINS", "").split(",") if d.strip()]

# 警告阈值（天）
WARNING_THRESHOLD = 30

# 连接超时时间（秒）
CONNECTION_TIMEOUT = 10

# ========== 日志配置 ==========
def setup_logging():
    """配置日志系统"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ========== 功能函数区域 ==========
def get_certificate_info(domain: str) -> Dict:
    """
    获取单个域名的SSL证书信息
    
    Args:
        domain: 域名（可以包含端口）
        
    Returns:
        dict: 证书信息字典，包含以下字段：
            - domain: 域名
            - expiry_date: 到期时间（datetime对象）
            - days_left: 剩余天数
            - issuer: 颁发者
            - is_valid: 是否有效
            - error: 错误信息（如有）
    """
    result = {
        "domain": domain,
        "expiry_date": datetime.min,
        "days_left": -1,
        "issuer": "",
        "is_valid": False,
        "error": None
    }
    
    try:
        # 解析域名和端口
        hostname = domain if ':' in domain else f'{domain}:443'
        host, port = hostname.split(':')
        port = int(port)
        
        # 创建SSL上下文
        context = ssl.create_default_context()
        
        # 建立连接并获取证书
        with socket.create_connection((host, port), timeout=CONNECTION_TIMEOUT) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
        
        # 解析证书信息
        expiry_str = cert['notAfter']
        expiry_date = datetime.strptime(expiry_str, '%b %d %H:%M:%S %Y %Z')
        
        # 计算剩余天数
        now = datetime.utcnow()
        days_left = (expiry_date - now).days
        
        # 获取颁发者信息
        issuer_dict = dict(x[0] for x in cert['issuer'])
        issuer = issuer_dict.get('organizationName', 'Unknown')
        
        # 更新结果
        result.update({
            "expiry_date": expiry_date,
            "days_left": days_left,
            "issuer": issuer,
            "is_valid": days_left > 0
        })
        
        logger.info(f"成功获取 {domain} 的证书信息，剩余{days_left}天")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"检查域名 {domain} 时出错: {error_msg}")
        result["error"] = error_msg
    
    return result

def check_all_domains(domains: List[str]) -> List[Dict]:
    """
    检查所有域名的SSL证书
    
    Args:
        domains: 域名列表
        
    Returns:
        list: 所有域名的证书信息列表
    """
    results = []
    logger.info(f"开始检查 {len(domains)} 个域名的SSL证书...")
    
    for domain in domains:
        logger.info(f"正在检查: {domain}")
        cert_info = get_certificate_info(domain)
        results.append(cert_info)
        
        # 记录单个结果
        if cert_info["is_valid"]:
            if cert_info["days_left"] <= WARNING_THRESHOLD:
                logger.warning(f"  ⚠️  {domain} 证书将在 {cert_info['days_left']} 天后过期")
            else:
                logger.info(f"  ✅ {domain} 证书正常，剩余 {cert_info['days_left']} 天")
        else:
            if cert_info["error"]:
                logger.error(f"  🔧 {domain} 检查失败: {cert_info['error']}")
            else:
                logger.error(f"  ❌ {domain} 证书已过期或无效")
    
    return results

def categorize_certificates(certificates: List[Dict]) -> Dict[str, List[Dict]]:
    """
    将证书结果分类
    
    Args:
        certificates: 证书信息列表
        
    Returns:
        dict: 分类后的证书，包含以下键：
            - warning: 即将过期的证书 (30天内)
            - expired: 已过期的证书
            - valid: 证书状态正常
            - error: 检查失败的域名
    """
    warning_certs = []
    expired_certs = []
    valid_certs = []
    error_certs = []
    
    for cert in certificates:
        if cert["error"] is not None:
            error_certs.append(cert)
        elif cert["is_valid"]:
            if 0 < cert["days_left"] <= WARNING_THRESHOLD:
                warning_certs.append(cert)
            elif cert["days_left"] > WARNING_THRESHOLD:
                valid_certs.append(cert)
        else:
            expired_certs.append(cert)
    
    return {
        "warning": warning_certs,
        "expired": expired_certs,
        "valid": valid_certs,
        "error": error_certs
    }

def format_certificate_report(certificates: List[Dict]) -> str:
    """
    格式化证书检查报告
    
    Args:
        certificates: 证书信息列表
        
    Returns:
        str: 格式化后的纯文本报告
    """
    # 分类证书
    categories = categorize_certificates(certificates)
    warning_certs = categories["warning"]
    expired_certs = categories["expired"]
    valid_certs = categories["valid"]
    error_certs = categories["error"]
    
    # 获取当前时间
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 构建报告
    lines = [f"🔔 SSL证书检查报告"]
    lines.append(f"⏰ 检查时间: {now}")
    lines.append(f"📊 总计: {len(certificates)} 个域名")
    lines.append("")
    
    # 已过期的证书
    if expired_certs:
        lines.append("❌ 已过期的证书:")
        for cert in expired_certs:
            expiry_date_str = cert["expiry_date"].strftime('%Y-%m-%d') if cert["expiry_date"] != datetime.min else "未知"
            lines.append(f"   • {cert['domain']} - 已过期 {abs(cert['days_left'])} 天")
            lines.append(f"     到期: {expiry_date_str}")
        lines.append("")
    
    # 即将过期的证书
    if warning_certs:
        lines.append("⚠️ 即将过期的证书 (30天内):")
        for cert in warning_certs:
            expiry_date_str = cert["expiry_date"].strftime('%Y-%m-%d')
            lines.append(f"   • {cert['domain']} - 剩余 {cert['days_left']} 天")
            lines.append(f"     到期: {expiry_date_str}")
            lines.append(f"     颁发: {cert['issuer']}")
        lines.append("")
    
    # 证书状态正常
    if valid_certs:
        lines.append("✅ 证书状态正常:")
        for cert in valid_certs:
            lines.append(f"   • {cert['domain']} - 剩余 {cert['days_left']} 天")
        lines.append("")
    
    # 检查失败的域名
    if error_certs:
        lines.append("🔧 检查失败的域名:")
        for cert in error_certs:
            lines.append(f"   • {cert['domain']} - 错误: {cert['error']}")
    
    # 添加统计信息
    lines.append("")
    lines.append("📈 统计信息:")
    lines.append(f"   ✅ 正常: {len(valid_certs)}")
    lines.append(f"   ⚠️  警告: {len(warning_certs)}")
    lines.append(f"   ❌ 过期: {len(expired_certs)}")
    lines.append(f"   🔧 失败: {len(error_certs)}")
    
    return "\n".join(lines)


# ========== 主函数 ==========
def main():
    """
    主函数 - 程序入口点
    """
    logger.info("=" * 50)
    logger.info("SSL证书检查脚本开始执行")
    logger.info("=" * 50)
    
    try:
        # 1. 检查所有域名的SSL证书
        cert_results = check_all_domains(DOMAINS_TO_CHECK)
        
        # 2. 格式化报告
        report = format_certificate_report(cert_results)
        
        # 3. 发送报告到Telegram
        notify_send("SSL证书检查报告", report)
        logger.info("SSL证书检查报告已发送")
        
        # 4. 在控制台打印摘要
        categories = categorize_certificates(cert_results)
        
        print("\n" + "=" * 60)
        print("SSL证书检查完成!")
        print(f"检查域名总数: {len(cert_results)}")
        print(f"正常: {len(categories['valid'])}")
        print(f"警告: {len(categories['warning'])}")
        print(f"过期: {len(categories['expired'])}")
        print(f"失败: {len(categories['error'])}")
        print("=" * 60)
        
        # 5. 如果有过期或即将过期的证书，显示警告
        if categories["expired"] or categories["warning"]:
            print("\n⚠️  需要注意的域名:")
            for cert in categories["expired"]:
                print(f"  ❌ {cert['domain']} - 已过期")
            for cert in categories["warning"]:
                print(f"  ⚠️  {cert['domain']} - 剩余{cert['days_left']}天到期")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("用户中断执行")
        return 130
        
    except Exception as e:
        logger.error(f"脚本执行过程中发生未捕获的异常: {e}")
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
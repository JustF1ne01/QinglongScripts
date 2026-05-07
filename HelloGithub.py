#!/usr/bin/env python3
"""
HelloGitHub 月刊更新提醒 Telegram 机器人
每月运行一次，检查并发送最新月刊内容。
支持分多条消息发送完整内容，基于字符长度分段。
"""

import json
import os
import requests
import logging
import re
import html          # 新增导入，用于HTML转义
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ========== 用户配置区域（从环境变量读取） ==========
# 1. Telegram 机器人配置
TELEGRAM_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TG_CHAT_ID", "")

# 2. 本地状态文件路径（用于记录上次发送的期数）
STATE_FILE = Path.home() / ".hellogithub_bot_state.json"

# 3. API 地址
PERIODICAL_API = "https://abroad.hellogithub.com/v1/periodical/"
PERIODICAL_PAGE_URL = "https://hellogithub.com/periodical"

# 4. 消息配置
MAX_MESSAGE_LENGTH = 3900  # Telegram消息最大长度，留有余量（4000 - 100）

# ========== 日志配置 ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_last_sent_volume() -> int:
    """加载上次已发送的期数"""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
                return state.get('last_sent_volume', 0)
        return 0
    except Exception as e:
        logger.error(f"读取状态文件失败: {e}")
        return 0

def save_last_sent_volume(volume_num: int) -> None:
    """保存最新发送的期数"""
    try:
        state = {
            'last_sent_volume': volume_num, 
            'updated_at': datetime.now().isoformat(),
            'last_run': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        logger.info(f"已更新状态文件，最新期数为: {volume_num}")
    except Exception as e:
        logger.error(f"保存状态文件失败: {e}")

def get_latest_volume_info() -> Tuple[Optional[int], Optional[str]]:
    """从API获取最新期数信息"""
    try:
        response = requests.get(PERIODICAL_API, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('success'):
            # volumes列表已按期数降序排列，第一个就是最新的
            latest_volume = data['volumes'][0]
            return latest_volume['num'], latest_volume['lastmod']
        else:
            logger.error("API返回success为false")
            return None, None
    except requests.exceptions.RequestException as e:
        logger.error(f"请求期数API失败: {e}")
        return None, None
    except (KeyError, IndexError) as e:
        logger.error(f"解析期数API响应失败: {e}")
        return None, None

def extract_build_id() -> Optional[str]:
    """从月刊页面提取buildId"""
    try:
        response = requests.get(PERIODICAL_PAGE_URL, timeout=10)
        response.raise_for_status()
        
        # 使用正则表达式提取__NEXT_DATA__中的内容
        pattern = r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'
        match = re.search(pattern, response.text, re.DOTALL)
        
        if match:
            next_data = json.loads(match.group(1))
            build_id = next_data.get('buildId')
            if build_id:
                logger.info(f"成功获取buildId: {build_id}")
                return build_id
            else:
                logger.error("在__NEXT_DATA__中未找到buildId")
                return None
        else:
            logger.error("未找到__NEXT_DATA__标签")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"请求月刊页面失败: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"解析__NEXT_DATA__ JSON失败: {e}")
        return None
    except Exception as e:
        logger.error(f"提取buildId失败: {e}")
        return None

def get_volume_content(volume_num: int, build_id: str) -> Optional[Dict]:
    """获取指定期数的详细内容"""
    content_api = f"https://hellogithub.com/_next/data/{build_id}/zh/periodical/volume/{volume_num}.json"
    
    try:
        response = requests.get(content_api, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # 根据API结构提取数据
        page_props = data.get('pageProps', {})
        
        # 尝试不同的数据路径
        volume_data = page_props.get('volumeData', {})
        if not volume_data:
            # 尝试另一种可能的路径
            if 'volume' in page_props:
                volume_data = page_props['volume']
        
        if volume_data:
            # 提取标题和描述
            title = volume_data.get('title', f'HelloGitHub 第 {volume_num} 期')
            desc = volume_data.get('desc', '')
            
            # 提取分类和项目数据
            categories_data = []
            if 'data' in volume_data and isinstance(volume_data['data'], list):
                for category_item in volume_data['data']:
                    category_name = category_item.get('category_name', '未分类')
                    items = category_item.get('items', [])
                    
                    # 格式化每个项目的数据
                    formatted_items = []
                    for item in items:
                        formatted_item = {
                            'full_name': item.get('full_name', '未知项目'),
                            'description': item.get('description', '暂无描述'),
                            'github_url': item.get('github_url', ''),
                            'stars': item.get('stars', 0),
                            'forks': item.get('forks', 0),
                            'watch': item.get('watch', 0),
                            'language': item.get('lang', ''),
                            'homepage': item.get('homepage', '')
                        }
                        formatted_items.append(formatted_item)
                    
                    if formatted_items:
                        categories_data.append({
                            'category_name': category_name,
                            'items': formatted_items
                        })
            
            return {
                'title': title,
                'description': desc,
                'categories': categories_data,
                'total_items': sum(len(cat['items']) for cat in categories_data),
                'volume_num': volume_num
            }
        else:
            logger.warning(f"期数 {volume_num} 的内容结构可能与预期不符")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"请求内容API失败 (期数 {volume_num}): {e}")
        return None
    except (KeyError, json.JSONDecodeError) as e:
        logger.error(f"解析内容API响应失败 (期数 {volume_num}): {e}")
        return None

def format_project_info(project: Dict, project_num: int, total_projects: int) -> str:
    """格式化单个项目的信息，并对用户内容进行HTML转义"""
    # 对可能包含HTML特殊字符的字段进行转义
    name = html.escape(project['full_name'])
    description = html.escape(project['description'])
    stars = project['stars']
    forks = project['forks']
    watch = project['watch']
    language = html.escape(project['language']) if project['language'] else ''
    github_url = project['github_url']  # URL本身不需要转义，但它是安全的（不含尖括号）
    
    # 格式化项目信息
    project_text = f"<b>{project_num}/{total_projects}. {name}</b>\n"
    
    if language:
        project_text += f"   📝 语言: <code>{language}</code>\n"
    
    project_text += f"   📖 描述: {description}\n"
    
    # GitHub数据
    stats = []
    if stars > 0:
        stats.append(f"⭐ {stars}")
    if forks > 0:
        stats.append(f"🔀 {forks}")
    if watch > 0:
        stats.append(f"👀 {watch}")
    
    if stats:
        project_text += f"   📊 数据: {' | '.join(stats)}\n"
    
    if github_url:
        project_text += f"   🔗 链接: {github_url}\n"
    
    return project_text + "\n"

def format_category_header(category: Dict, category_num: int, total_categories: int) -> str:
    """格式化分类标题，对分类名称进行转义"""
    category_name = html.escape(category['category_name'])
    items = category['items']
    
    category_header = f"\n{'='*40}\n\n"
    category_header += f"<b>🎯 {category_num}/{total_categories}. {category_name} ({len(items)}个项目)</b>\n\n"
    
    return category_header

def create_message_messages(content: Dict) -> List[str]:
    """创建要发送的消息列表，基于字符长度进行智能分段"""
    if not content:
        return []
    
    title = html.escape(content['title'])          # 标题也转义
    desc = html.escape(content['description']) if content['description'] else ''
    categories = content.get('categories', [])
    total_items = content.get('total_items', 0)
    volume_num = content.get('volume_num', 0)
    total_categories = len(categories)
    
    messages = []
    
    # 第一步：创建标题和概要消息
    header_message = f"🚀 <b>{title}</b>\n\n"
    
    if desc:
        header_message += f"📝 {desc}\n\n"
    
    # 解析发布时间
    latest_num, lastmod = get_latest_volume_info()
    if lastmod:
        pub_date = lastmod[:10]
    else:
        pub_date = datetime.now().strftime('%Y-%m-%d')
    
    header_message += f"📅 发布时间: {pub_date}\n"
    header_message += f"🔢 期号: 第 {volume_num} 期\n"
    header_message += f"📚 项目总数: {total_items} 个\n"
    header_message += f"🏷️ 分类数量: {total_categories} 个\n\n"
    header_message += f"⏳ 正在发送完整项目信息，请稍候...\n\n"
    header_message += "="*40 + "\n"
    
    messages.append(header_message)
    
    # 第二步：准备所有内容片段
    all_content_parts = []
    
    # 按顺序添加所有分类和项目
    current_category_num = 1
    for category in categories:
        # 添加分类标题
        category_header = format_category_header(category, current_category_num, total_categories)
        all_content_parts.append(("category_header", category_header))
        
        # 添加每个项目
        category_items = category['items']
        for i, item in enumerate(category_items):
            project_num = sum(len(cat['items']) for cat in categories[:current_category_num-1]) + i + 1
            project_text = format_project_info(item, project_num, total_items)
            all_content_parts.append(("project", project_text))
        
        current_category_num += 1
    
    # 第三步：智能分段，基于字符长度
    current_message = ""
    current_message_parts = []
    
    for part_type, part_text in all_content_parts:
        # 检查添加新部分后是否会超过长度限制
        if len(current_message) + len(part_text) <= MAX_MESSAGE_LENGTH:
            current_message += part_text
            current_message_parts.append((part_type, part_text))
        else:
            # 当前消息已满，保存它
            if current_message:
                # 为消息添加标题
                if len(messages) == 1:
                    # 第一条内容消息
                    message_with_header = f"<b>📋 第 {volume_num} 期 - 项目详情 (第 1 部分)</b>\n\n"
                else:
                    # 后续内容消息
                    message_with_header = f"<b>📋 第 {volume_num} 期 - 项目详情 (第 {len(messages)} 部分)</b>\n\n"
                
                message_with_header += current_message
                messages.append(message_with_header)
            
            # 开始新消息
            current_message = part_text
            current_message_parts = [(part_type, part_text)]
            
            # 如果单个部分就超过限制（很少见），需要特殊处理
            if len(part_text) > MAX_MESSAGE_LENGTH:
                logger.warning(f"发现超长部分 ({len(part_text)} 字符)，将进行分割")
                # 分割超长部分
                split_parts = split_long_text(part_text, MAX_MESSAGE_LENGTH)
                for split_part in split_parts:
                    if split_part:
                        messages.append(split_part)
                current_message = ""
                current_message_parts = []
    
    # 添加最后一条消息
    if current_message:
        if len(messages) == 1:
            message_with_header = f"<b>📋 第 {volume_num} 期 - 项目详情 (第 1 部分)</b>\n\n"
        else:
            message_with_header = f"<b>📋 第 {volume_num} 期 - 项目详情 (第 {len(messages)} 部分)</b>\n\n"
        
        message_with_header += current_message
        messages.append(message_with_header)
    
    # 第四步：添加总结消息
    footer_message = f"\n{'='*40}\n\n"
    footer_message += f"<b>🎉 {title} 完整内容已发送完毕！</b>\n\n"
    footer_message += f"📊 本期共包含 {total_items} 个项目，"
    footer_message += f"分为 {total_categories} 个分类，"
    footer_message += f"共分 {len(messages)} 条消息发送。\n\n"
    
    # 添加阅读链接
    read_more_url = f"https://hellogithub.com/zh/periodical/volume/{volume_num}/"
    footer_message += f"🔗 在线阅读: {read_more_url}\n\n"
    
    # 添加GitHub链接
    github_url = "https://github.com/521xueweihan/HelloGitHub"
    footer_message += f"🌟 HelloGitHub项目: {github_url}\n\n"
    
    footer_message += "感谢使用 HelloGitHub 月刊机器人！"
    
    messages.append(footer_message)
    
    return messages

def split_long_text(text: str, max_length: int) -> List[str]:
    """分割超长文本为多个部分"""
    if len(text) <= max_length:
        return [text]
    
    parts = []
    
    # 尝试按项目分割
    project_pattern = r'<b>\d+/\d+\. .*?</b>.*?(?=<b>\d+/\d+\. |\Z)'
    projects = re.findall(project_pattern, text, re.DOTALL)
    
    if projects:
        current_part = ""
        for project in projects:
            if len(current_part) + len(project) <= max_length:
                current_part += project
            else:
                if current_part:
                    parts.append(current_part)
                current_part = project
        
        if current_part:
            parts.append(current_part)
    else:
        # 如果无法按项目分割，按固定长度分割
        for i in range(0, len(text), max_length):
            part = text[i:i + max_length]
            if i > 0:
                part = f"<i>(续前文)</i>\n\n{part}"
            parts.append(part)
    
    return parts

def send_telegram_message(message: str) -> bool:
    """发送单条消息到Telegram"""
    if not message or len(message.strip()) == 0:
        return False
    
    telegram_api = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': False
    }
    
    try:
        response = requests.post(telegram_api, data=payload, timeout=30)
        result = response.json()
        
        if result.get('ok'):
            logger.info("Telegram消息发送成功！")
            return True
        else:
            error_desc = result.get('description', '未知错误')
            logger.error(f"Telegram消息发送失败: {error_desc}")
            
            # 如果消息太长，尝试进一步分割
            if "Message is too long" in error_desc:
                logger.warning("消息过长，尝试进一步分割...")
                split_messages = split_long_text(message, MAX_MESSAGE_LENGTH - 500)
                
                all_success = True
                for i, msg_part in enumerate(split_messages):
                    if i > 0:
                        msg_part = f"<i>(续第{i}部分)</i>\n\n{msg_part}"
                    
                    if not send_telegram_direct(msg_part):
                        all_success = False
                    
                    # 避免发送过快
                    if i < len(split_messages) - 1:
                        import time
                        time.sleep(1)
                
                return all_success
            
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"请求Telegram API失败: {e}")
        return False
    except Exception as e:
        logger.error(f"发送消息时发生未知错误: {e}")
        return False

def send_telegram_direct(message: str) -> bool:
    """直接发送消息到Telegram（不带分割逻辑）"""
    telegram_api = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': False
    }
    
    try:
        response = requests.post(telegram_api, data=payload, timeout=30)
        result = response.json()
        
        if result.get('ok'):
            return True
        else:
            logger.error(f"直接发送失败: {result.get('description')}")
            return False
    except Exception as e:
        logger.error(f"直接发送异常: {e}")
        return False

def send_all_messages(messages: List[str]) -> bool:
    """发送所有消息，每条消息之间添加延迟"""
    if not messages:
        return False
    
    all_success = True
    
    for i, message in enumerate(messages):
        logger.info(f"正在发送第 {i+1}/{len(messages)} 条消息 (长度: {len(message)} 字符)...")
        
        if not send_telegram_message(message):
            all_success = False
            logger.error(f"第 {i+1} 条消息发送失败")
        
        # 在消息之间添加延迟，避免被Telegram限制
        if i < len(messages) - 1:
            import time
            time.sleep(2)  # 2秒延迟
    
    return all_success

def main():
    """主函数"""
    logger.info("===== HelloGitHub月刊检查开始 =====")
    
    # 1. 加载上次发送的期数
    last_sent = load_last_sent_volume()
    logger.info(f"上次发送的期数: {last_sent}")
    
    # 2. 获取最新期数信息
    latest_num, lastmod = get_latest_volume_info()
    if not latest_num:
        logger.error("无法获取最新期数信息，任务终止")
        return
    
    logger.info(f"最新期数: {latest_num}, 更新时间: {lastmod}")
    
    # 3. 检查是否有新刊
    if latest_num <= last_sent:
        logger.info(f"没有新刊发布 (最新: {latest_num}, 已发送: {last_sent})")
        return
    
    logger.info(f"发现新刊! 第 {latest_num} 期")
    
    # 4. 获取buildId
    build_id = extract_build_id()
    if not build_id:
        logger.error("无法获取buildId，任务终止")
        return
    
    # 5. 获取新刊内容
    content = get_volume_content(latest_num, build_id)
    if not content:
        logger.error(f"无法获取第 {latest_num} 期内容")
        return
    
    logger.info(f"成功获取第 {latest_num} 期内容，包含 {content.get('total_items', 0)} 个项目")
    
    # 6. 创建消息列表
    messages = create_message_messages(content)
    if not messages:
        logger.error("创建消息失败")
        return
    
    logger.info(f"共生成 {len(messages)} 条消息")
    
    # 统计消息长度
    for i, msg in enumerate(messages):
        logger.info(f"消息 {i+1}: {len(msg)} 字符")
    
    # 7. 发送所有消息
    if send_all_messages(messages):
        # 8. 更新状态
        save_last_sent_volume(latest_num)
        logger.info("===== 任务完成 =====")
    else:
        logger.error("消息发送失败，状态未更新")

if __name__ == "__main__":
    main()
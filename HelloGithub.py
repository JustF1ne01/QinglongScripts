#!/usr/bin/env python3
# new Env('HelloGithub月刊')
# cron: 0 8 1 * *
"""
HelloGitHub 月刊更新提醒
每月运行一次，检查并发送最新月刊内容。
"""

import json
import requests
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple
from notify import send as notify_send

# ========== 配置 ==========
STATE_FILE = Path.home() / ".hellogithub_bot_state.json"
PERIODICAL_API = "https://abroad.hellogithub.com/v1/periodical/"
PERIODICAL_PAGE_URL = "https://hellogithub.com/periodical"

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

def build_message(content: Dict) -> str:
    """构建通知消息"""
    if not content:
        return ""

    title = content['title']
    categories = content.get('categories', [])
    total_items = content.get('total_items', 0)
    volume_num = content.get('volume_num', 0)

    lines = []
    lines.append(f"📅 发布时间: {datetime.now().strftime('%Y-%m-%d')}")
    lines.append(f"🔢 期号: 第 {volume_num} 期")
    lines.append(f"📚 项目总数: {total_items} 个")
    lines.append(f"🏷️ 分类数量: {len(categories)} 个")
    lines.append("")

    for i, category in enumerate(categories, 1):
        cat_name = category['category_name']
        cat_count = len(category['items'])
        lines.append(f"  {i}. {cat_name} ({cat_count}个项目)")

    lines.append("")
    read_more_url = f"https://hellogithub.com/zh/periodical/volume/{volume_num}/"
    lines.append(f"🔗 在线阅读: {read_more_url}")
    lines.append(f"🌟 项目地址: https://github.com/521xueweihan/HelloGitHub")

    return "\n".join(lines)

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
    
    # 6. 构建并发送通知
    message = build_message(content)
    notify_send(f"HelloGitHub 第 {latest_num} 期", message)
    save_last_sent_volume(latest_num)
    logger.info("===== 任务完成 =====")

if __name__ == "__main__":
    main()
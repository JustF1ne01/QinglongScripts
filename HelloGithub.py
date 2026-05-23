#!/usr/bin/env python3
"""
cron: 0 8 1 * *
new Env("HelloGitHub月刊")
HelloGitHub 月刊更新提醒
每月运行一次，检查并发送最新月刊内容。
支持分多条消息发送完整内容，基于字符长度分段。
"""

import json
import os
import re
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from utils import log_info, log_success, log_warning, log_error, beijing_time_str
from notifier import send as notify_send

# ==================== 用户配置 ====================
STATE_FILE = Path.home() / ".hellogithub_bot_state.json"
PERIODICAL_API = "https://abroad.hellogithub.com/v1/periodical/"
PERIODICAL_PAGE_URL = "https://hellogithub.com/periodical"
MAX_MESSAGE_LENGTH = 3900


def load_last_sent_volume() -> int:
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("last_sent_volume", 0)
        return 0
    except Exception as e:
        log_error(f"读取状态文件失败: {e}")
        return 0


def save_last_sent_volume(volume_num: int) -> None:
    try:
        state = {"last_sent_volume": volume_num, "updated_at": datetime.now().isoformat(), "last_run": beijing_time_str()}
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        log_success(f"已更新状态文件，最新期数: {volume_num}")
    except Exception as e:
        log_error(f"保存状态文件失败: {e}")


def get_latest_volume_info() -> Tuple[Optional[int], Optional[str]]:
    try:
        resp = requests.get(PERIODICAL_API, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("success"):
            latest = data["volumes"][0]
            return latest["num"], latest["lastmod"]
        log_error("API 返回 success 为 false")
        return None, None
    except Exception as e:
        log_error(f"请求期数 API 失败: {e}")
        return None, None


def extract_build_id() -> Optional[str]:
    try:
        resp = requests.get(PERIODICAL_PAGE_URL, timeout=10)
        resp.raise_for_status()
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', resp.text, re.DOTALL)
        if match:
            next_data = json.loads(match.group(1))
            build_id = next_data.get("buildId")
            if build_id:
                log_info(f"成功获取 buildId: {build_id}")
                return build_id
        log_error("未找到 buildId")
        return None
    except Exception as e:
        log_error(f"提取 buildId 失败: {e}")
        return None


def get_volume_content(volume_num: int, build_id: str) -> Optional[Dict]:
    content_api = f"https://hellogithub.com/_next/data/{build_id}/zh/periodical/volume/{volume_num}.json"
    try:
        data = requests.get(content_api, timeout=10).json()
        page_props = data.get("pageProps", {})
        volume_data = page_props.get("volumeData") or page_props.get("volume", {})
        if not volume_data:
            return None

        title = volume_data.get("title", f"HelloGitHub 第 {volume_num} 期")
        desc = volume_data.get("desc", "")
        categories_data = []
        for category_item in volume_data.get("data", []):
            formatted_items = []
            for item in category_item.get("items", []):
                formatted_items.append({
                    "full_name": item.get("full_name", "未知项目"),
                    "description": item.get("description", "暂无描述"),
                    "github_url": item.get("github_url", ""),
                    "stars": item.get("stars", 0),
                    "forks": item.get("forks", 0),
                    "watch": item.get("watch", 0),
                    "language": item.get("lang", ""),
                    "homepage": item.get("homepage", ""),
                })
            if formatted_items:
                categories_data.append({"category_name": category_item.get("category_name", "未分类"), "items": formatted_items})

        return {"title": title, "description": desc, "categories": categories_data, "total_items": sum(len(c["items"]) for c in categories_data), "volume_num": volume_num}
    except Exception as e:
        log_error(f"请求内容 API 失败: {e}")
        return None


def format_project_info(project: Dict, project_num: int, total_projects: int) -> str:
    name = project["full_name"]
    desc = project["description"]
    stars, forks, watch = project["stars"], project["forks"], project["watch"]
    lang = project["language"]
    github_url = project["github_url"]
    lines = [f"  {project_num}/{total_projects}. 【{name}】"]
    if lang:
        lines.append(f"     语言: {lang}")
    lines.append(f"     描述: {desc}")
    stats = []
    if stars > 0: stats.append(f"⭐ {stars}")
    if forks > 0: stats.append(f"🔀 {forks}")
    if watch > 0: stats.append(f"👀 {watch}")
    if stats:
        lines.append(f"     数据: {' | '.join(stats)}")
    if github_url:
        lines.append(f"     链接: {github_url}")
    lines.append("")
    return "\n".join(lines)


def format_category_header(category: Dict, category_num: int, total_categories: int) -> str:
    category_name = category["category_name"]
    items = category["items"]
    return f"\n{'─' * 40}\n\n🎯 {category_num}/{total_categories}. {category_name} ({len(items)} 个项目)\n\n"


def create_report_pages(content: Dict) -> List[str]:
    if not content:
        return []

    title = content["title"]
    desc = content["description"]
    categories = content.get("categories", [])
    total_items = content.get("total_items", 0)
    volume_num = content.get("volume_num", 0)
    total_categories = len(categories)

    latest_num, lastmod = get_latest_volume_info()
    pub_date = lastmod[:10] if lastmod else beijing_time_str("%Y-%m-%d")

    # 标题页
    header = f"🚀 {title}\n\n"
    if desc:
        header += f"📝 {desc}\n\n"
    header += f"📅 发布时间: {pub_date}\n🔢 期号: 第 {volume_num} 期\n📚 项目总数: {total_items} 个\n🏷️ 分类数量: {total_categories} 个\n\n{'─' * 40}\n"
    pages = [header]

    all_parts = []
    cat_num = 1
    for cat in categories:
        all_parts.append(format_category_header(cat, cat_num, total_categories))
        for i, item in enumerate(cat["items"]):
            proj_num = sum(len(c["items"]) for c in categories[:cat_num - 1]) + i + 1
            all_parts.append(format_project_info(item, proj_num, total_items))
        cat_num += 1

    current = ""
    for part in all_parts:
        if len(current) + len(part) <= MAX_MESSAGE_LENGTH:
            current += part
        else:
            if current:
                pages.append(f"📋 第 {volume_num} 期 - 项目详情\n\n{current}")
            current = part
            if len(part) > MAX_MESSAGE_LENGTH:
                pages.append(part)
                current = ""
    if current:
        pages.append(f"📋 第 {volume_num} 期 - 项目详情\n\n{current}")

    read_more = f"https://hellogithub.com/zh/periodical/volume/{volume_num}/"
    footer = f"\n{'─' * 40}\n\n🎉 {title} 完整内容已发送完毕！\n\n📊 本期共 {total_items} 个项目，{total_categories} 个分类\n🔗 在线阅读: {read_more}\n🌟 GitHub: https://github.com/521xueweihan/HelloGitHub"
    pages.append(footer)
    return pages


def main():
    log_info("===== HelloGitHub 月刊检查开始 =====")
    last_sent = load_last_sent_volume()
    log_info(f"上次发送的期数: {last_sent}")

    latest_num, lastmod = get_latest_volume_info()
    if not latest_num:
        log_error("无法获取最新期数信息，任务终止")
        return

    log_info(f"最新期数: {latest_num}, 更新时间: {lastmod}")
    if latest_num <= last_sent:
        log_info(f"没有新刊发布 (最新: {latest_num}, 已发送: {last_sent})")
        return

    log_info(f"发现新刊! 第 {latest_num} 期")
    build_id = extract_build_id()
    if not build_id:
        log_error("无法获取 buildId，任务终止")
        return

    content = get_volume_content(latest_num, build_id)
    if not content:
        log_error(f"无法获取第 {latest_num} 期内容")
        return

    log_success(f"成功获取第 {latest_num} 期内容，包含 {content.get('total_items', 0)} 个项目")

    pages = create_report_pages(content)
    log_info(f"共生成 {len(pages)} 条消息")

    for i, page_text in enumerate(pages, 1):
        log_info(f"正在发送第 {i}/{len(pages)} 条消息 ({len(page_text)} 字符)...")
        notify_send(f"HelloGitHub 第 {latest_num} 期 ({i}/{len(pages)})", page_text)
        if i < len(pages):
            time.sleep(2)

    save_last_sent_volume(latest_num)
    log_info("===== 任务完成 =====")


if __name__ == "__main__":
    main()

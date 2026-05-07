#!/usr/bin/env python3
# new Env('B站每日任务')
# cron: 0 0 * * *
"""
Bilibili 每日任务脚本
实现以下功能：
- 漫画签到
- 投币任务（支持指定投币数和投币来源）
- 观看视频任务
- 分享视频任务
- 银瓜子兑换硬币（可选）
- 获取今日经验、当前经验、预计升级天数等信息
"""

import os
import time
import requests
from notify import send as notify_send

# ==================== 用户配置（从环境变量读取）====================
BILIBILI_COOKIE = os.environ.get("BILIBILI_COOKIE", "")
COIN_NUM = int(os.environ.get("BILIBILI_COIN_NUM", "0"))           # 每日目标投币数，默认为0
COIN_TYPE = int(os.environ.get("BILIBILI_COIN_TYPE", "1"))         # 投币来源：1-优先关注列表，其他-随机分区视频
SILVER2COIN = os.environ.get("BILIBILI_SILVER2COIN", "false").lower() == "true"  # 是否开启银瓜子兑换硬币

# ===================================================================

# 全局变量用于收集推送摘要的关键信息
report_data = {}

# 日志函数（无颜色，仅带级别和时间戳）
def log_info(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[INFO] {timestamp} - {msg}")

def log_success(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[SUCCESS] {timestamp} - {msg}")

def log_warning(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[WARNING] {timestamp} - {msg}")

def log_error(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[ERROR] {timestamp} - {msg}")

def log_normal(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"{timestamp} - {msg}")

# ---------- Bilibili API 函数 ----------
def get_nav(session):
    """获取用户导航信息（昵称、uid、登录状态、硬币数、大会员类型、当前经验）"""
    url = "https://api.bilibili.com/x/web-interface/nav"
    ret = session.get(url=url).json()
    uname = ret.get("data", {}).get("uname")
    uid = ret.get("data", {}).get("mid")
    is_login = ret.get("data", {}).get("isLogin")
    coin = ret.get("data", {}).get("money")
    vip_type = ret.get("data", {}).get("vipType")
    current_exp = ret.get("data", {}).get("level_info", {}).get("current_exp")
    return uname, uid, is_login, coin, vip_type, current_exp

def get_today_exp(session):
    """获取今日经验明细"""
    url = "https://api.bilibili.com/x/member/web/exp/log?jsonp=jsonp"
    today = time.strftime("%Y-%m-%d", time.localtime())
    try:
        data_list = session.get(url=url).json().get("data", {}).get("list", [])
        return list(filter(lambda x: x["time"].split()[0] == today, data_list))
    except:
        return []

def manga_sign(session, platform="android"):
    """漫画签到"""
    try:
        url = "https://manga.bilibili.com/twirp/activity.v1.Activity/ClockIn"
        post_data = {"platform": platform}
        ret = session.post(url=url, data=post_data).json()
        if ret["code"] == 0:
            msg = "✅ 签到成功"
        elif ret.get("msg") == "clockin clockin is duplicate":
            msg = "✅ 今天已经签到过了"
        else:
            msg = f"❌ 签到失败：{ret.get('msg', '未知错误')}"
            log_error(msg)
    except Exception as e:
        msg = f"❌ 签到异常：{e!s}"
        log_error(msg)
    return msg

def report_task(session, bili_jct, aid, cid, progres=300):
    """上报视频观看进度"""
    url = "http://api.bilibili.com/x/v2/history/report"
    post_data = {"aid": aid, "cid": cid, "progres": progres, "csrf": bili_jct}
    ret = session.post(url=url, data=post_data).json()
    return ret

def share_task(session, bili_jct, aid):
    """分享视频"""
    url = "https://api.bilibili.com/x/web-interface/share/add"
    post_data = {"aid": aid, "csrf": bili_jct}
    ret = session.post(url=url, data=post_data).json()
    return ret

def get_followings(session, uid, pn=1, ps=50, order="desc", order_type="attention"):
    """获取用户关注的up主列表"""
    params = {
        "vmid": uid,
        "pn": pn,
        "ps": ps,
        "order": order,
        "order_type": order_type,
    }
    url = "https://api.bilibili.com/x/relation/followings"
    ret = session.get(url=url, params=params).json()
    return ret

def space_arc_search(session, uid, pn=1, ps=30, tid=0, order="pubdate", keyword=""):
    """获取指定up主的视频投稿"""
    params = {
        "mid": uid,
        "pn": pn,
        "Ps": ps,
        "tid": tid,
        "order": order,
        "keyword": keyword,
    }
    url = "https://api.bilibili.com/x/space/arc/search"
    ret = session.get(url=url, params=params).json()
    count = 2  # 默认取前2个视频
    data_list = [
        {
            "aid": one.get("aid"),
            "cid": 0,
            "title": one.get("title"),
            "owner": one.get("author"),
        }
        for one in ret.get("data", {}).get("list", {}).get("vlist", [])[:count]
    ]
    return data_list, count

def coin_add(session, bili_jct, aid, num=1, select_like=1):
    """给视频投币"""
    url = "https://api.bilibili.com/x/web-interface/coin/add"
    post_data = {
        "aid": aid,
        "multiply": num,
        "select_like": select_like,
        "cross_domain": "true",
        "csrf": bili_jct,
    }
    ret = session.post(url=url, data=post_data).json()
    return ret

def live_status(session):
    """获取直播瓜子状态"""
    url = "https://api.live.bilibili.com/pay/v1/Exchange/getStatus"
    ret = session.get(url=url).json()
    data = ret.get("data", {})
    silver = data.get("silver", 0)
    gold = data.get("gold", 0)
    coin = data.get("coin", 0)
    return {"coin": coin, "gold": gold, "silver": silver}

def get_region(session, rid=1, num=6):
    """获取分区视频列表"""
    url = f"https://api.bilibili.com/x/web-interface/dynamic/region?ps={num}&rid={rid}"
    ret = session.get(url=url).json()
    data_list = [
        {
            "aid": one.get("aid"),
            "cid": one.get("cid"),
            "title": one.get("title"),
            "owner": one.get("owner", {}).get("name"),
        }
        for one in ret.get("data", {}).get("archives", [])
    ]
    return data_list

def silver2coin(session, bili_jct):
    """银瓜子兑换硬币"""
    url = "https://api.live.bilibili.com/xlive/revenue/v1/wallet/silver2coin"
    post_data = {"csrf": bili_jct}
    ret = session.post(url=url, data=post_data).json()
    return ret

def main():
    global report_data
    report_data = {}  # 重置报告数据

    # 解析cookie
    bilibili_cookie = {item.split("=")[0]: item.split("=")[1] for item in BILIBILI_COOKIE.split("; ")}
    bili_jct = bilibili_cookie.get("bili_jct")

    # 创建session并设置cookie和headers
    session = requests.session()
    requests.utils.add_dict_to_cookiejar(session.cookies, bilibili_cookie)
    session.headers.update({
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.64",
        "Referer": "https://www.bilibili.com/",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Connection": "keep-alive",
    })

    # 获取用户信息，检查登录状态
    uname, uid, is_login, coin, vip_type, current_exp = get_nav(session=session)
    if not is_login:
        log_error("登录失败，请检查cookie")
        return "登录失败，请检查cookie"

    log_success(f"登录成功，用户名：{uname}，UID：{uid}，当前硬币：{coin}")
    report_data["账号"] = uname

    # 漫画签到
    manhua_msg = manga_sign(session=session)
    log_info(f"漫画签到：{manhua_msg}")
    report_data["漫画签到"] = manhua_msg

    # 获取分区视频列表（备选）
    aid_list = get_region(session=session)

    # 计算今日已投币数
    today_exp_list = get_today_exp(session=session)
    coins_av_count = len(list(filter(lambda x: x.get("reason") == "视频投币奖励", today_exp_list)))
    need_coin_num = COIN_NUM - coins_av_count
    need_coin_num = need_coin_num if need_coin_num < coin else coin  # 不能超过现有硬币数

    log_info(f"今日已投币 {coins_av_count} 个，目标投币 {COIN_NUM} 个，还需投 {need_coin_num} 个")

    # 根据coin_type选择投币来源
    if COIN_TYPE == 1:
        following_list = get_followings(session=session, uid=uid)
        count = 0
        for following in following_list.get("data", {}).get("list", []):
            mid = following.get("mid")
            if mid:
                tmplist, tmpcount = space_arc_search(session=session, uid=mid)
                aid_list += tmplist
                count += tmpcount
                if count > need_coin_num:
                    log_info("已获取足够关注用户的视频")
                    break
        else:
            # 如果关注列表不足，补充分区视频
            aid_list += get_region(session=session)

    # 投币循环
    success_count = 0
    if need_coin_num > 0:
        for one in aid_list[::-1]:
            ret = coin_add(session=session, aid=one.get("aid"), bili_jct=bili_jct)
            if ret.get("code") == 0:
                need_coin_num -= 1
                log_success(f"成功给《{one.get('title')}》投一个币")
                success_count += 1
            elif ret.get("code") == 34005:
                log_warning(f"投币《{one.get('title')}》失败：{ret.get('message')}，继续下一个")
                continue
            else:
                log_error(f"投币《{one.get('title')}》失败：{ret.get('message')}，跳过投币")
                break
            if need_coin_num <= 0:
                break
        coin_msg = f"今日成功投币 {success_count + coins_av_count}/{COIN_NUM} 个"
    else:
        coin_msg = f"今日成功投币 {coins_av_count}/{COIN_NUM} 个"
    log_info(coin_msg)
    report_data["投币任务"] = coin_msg

    # 观看视频任务（使用第一个视频）
    if aid_list:
        first = aid_list[0]
        aid = first.get("aid")
        cid = first.get("cid")
        title = first.get("title")
        report_ret = report_task(session=session, bili_jct=bili_jct, aid=aid, cid=cid)
        if report_ret.get("code") == 0:
            report_msg = f"✅ 观看《{title}》300秒"
            log_success(report_msg)
        else:
            report_msg = f"❌ 观看任务失败"
            log_error(report_msg)

        share_ret = share_task(session=session, bili_jct=bili_jct, aid=aid)
        if share_ret.get("code") == 0:
            share_msg = f"✅ 分享《{title}》成功"
            log_success(share_msg)
        else:
            share_msg = f"❌ 分享失败"
            log_error(share_msg)
    else:
        report_msg = "⚠️ 无视频可观看"
        share_msg = "⚠️ 无视频可分享"
        log_warning(report_msg)
        log_warning(share_msg)
    report_data["观看视频"] = report_msg
    report_data["分享任务"] = share_msg

    # 银瓜子兑换硬币
    s2c_msg = "⚪ 未开启兑换"
    if SILVER2COIN:
        silver2coin_ret = silver2coin(session=session, bili_jct=bili_jct)
        if silver2coin_ret.get("code") == 0:
            s2c_msg = "✅ 银瓜子兑换硬币成功"
            log_success(s2c_msg)
        else:
            s2c_msg = f"❌ 兑换失败：{silver2coin_ret.get('message', '未知错误')}"
            log_error(s2c_msg)
    report_data["瓜子兑换"] = s2c_msg

    # 获取直播瓜子状态
    live_stats = live_status(session=session)
    report_data["硬币数量"] = live_stats["coin"]
    report_data["金瓜子数"] = live_stats["gold"]
    report_data["银瓜子数"] = live_stats["silver"]

    # 再次获取用户信息，更新硬币和经验
    uname, uid, is_login, new_coin, vip_type, new_current_exp = get_nav(session=session)
    today_exp = sum(map(lambda x: x.get("delta", 0), get_today_exp(session=session)))
    update_data = (28800 - new_current_exp) // (today_exp if today_exp else 1) if today_exp else "未知"

    report_data["今日经验"] = today_exp
    report_data["当前经验"] = new_current_exp
    report_data["升级还需"] = f"{update_data}天"

    # 在控制台打印最终汇总（可选）
    log_success("\n========== 任务执行汇总 ==========")
    for k, v in report_data.items():
        log_info(f"{k}: {v}")

    return report_data

def build_message(data):
    """构建纯文本推送消息"""
    lines = []
    lines.append("🎯 Bilibili 每日任务报告\n")

    # 账号信息
    lines.append(f"👤 账号：{data.get('账号', '未知')}")

    # 任务状态（用表情区分）
    tasks = [
        ("📖 漫画签到", data.get('漫画签到', '')),
        ("📺 观看视频", data.get('观看视频', '')),
        ("🔗 分享任务", data.get('分享任务', '')),
        ("💰 投币任务", data.get('投币任务', '')),
        ("💱 瓜子兑换", data.get('瓜子兑换', '')),
    ]
    for name, value in tasks:
        lines.append(f"{name}：{value}")

    # 经验与瓜子
    lines.append("\n📊 数据统计")
    lines.append(f"⭐ 今日经验：{data.get('今日经验', 0)}")
    lines.append(f"📈 当前经验：{data.get('当前经验', 0)}")
    lines.append(f"⏳ 升级还需：{data.get('升级还需', '未知')}")

    lines.append("\n🥜 瓜子库存")
    lines.append(f"🪙 硬币数量：{data.get('硬币数量', 0)}")
    lines.append(f"✨ 金瓜子数：{data.get('金瓜子数', 0)}")
    lines.append(f"🥈 银瓜子数：{data.get('银瓜子数', 0)}")

    lines.append("\n———————————————")
    lines.append(f"🕒 执行时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")

    return "\n".join(lines)

if __name__ == "__main__":
    report = main()
    if report:
        message = build_message(report)
        notify_send("Bilibili每日任务报告", message)
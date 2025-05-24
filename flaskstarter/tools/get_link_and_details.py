import re
from typing import Dict
import requests
import json
import time
import hashlib
import urllib.parse
from ..tools.config import COOKIE_PATH

import json
import os


def get_comment_details(oid: int, type: int, rpid: int) -> Dict:
    # 从 cookie 文件中获取 csrf token 和完整的 cookie 字符串
    cookie_str = ""
    csrf_token = ""
    try:
        with open(COOKIE_PATH, "r") as f:
            cookie_str = f.read()
            # 从 cookie 字符串中提取 bili_jct (csrf token)
            match = re.search(r"bili_jct=([^;]+)", cookie_str)
            if match:
                csrf_token = match.group(1)
            else:
                print("警告: 未在Cookie中找到 bili_jct (CSRF Token)。")
    except FileNotFoundError:
        print(f"错误: Cookie文件未找到于 {COOKIE_PATH}。")
        return {"success": False, "message": f"Cookie文件未找到于 {COOKIE_PATH}。"}
    except Exception as e:
        print(f"读取Cookie文件失败: {e}")
        return {"success": False, "message": f"读取Cookie文件失败: {e}"}
    if not csrf_token:
        return {"success": False, "message": "未获取到有效的CSRF Token (bili_jct)。"}
    # pagination_str 对于 detail API 似乎通常是空的或默认值
    pagination_str = '{"offset":""}'
    # 构建 URL
    # 注意：你提供的URL中没有w_rid和wts，表明这个API可能不需要WBI签名
    # 如果实际测试发现需要，则需要重新引入WBI签名逻辑
    url = (
        f"https://api.bilibili.com/x/v2/reply/detail?"
        f"csrf={csrf_token}&oid={oid}&pagination_str={urllib.parse.quote(pagination_str)}&root={rpid}&type={type}"
    )
    headers = {
        "Cookie": cookie_str,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0",
    }
    try:
        response = requests.get(url=url, headers=headers, timeout=15)
        response.raise_for_status()
        data = json.loads(response.content.decode("utf-8"))
        if data.get("code") != 0:
            return {"success": False, "message": data.get("message", "API返回错误")}
        comment_info_raw = data["data"].get("root")
        if not comment_info_raw:
            return {
                "success": False,
                "message": f"未找到rpid为{rpid}的评论或评论已被删除。",
            }
        member_info = comment_info_raw["member"]
        reply_control_info = comment_info_raw.get("reply_control", {})
        ip_location = reply_control_info.get("location", "")
        if ip_location.startswith("IP属地："):
            ip_location = ip_location[5:]  # 移除 "IP属地："前缀
        result = {
            "success": True,
            "comment_info": {
                "mid": member_info["mid"],  # 用户ID
                "name": member_info["uname"],  # 用户名
                "level": member_info["level_info"]["current_level"],  # 用户等级
                "sex": member_info["sex"],  # 性别
                "sign": member_info.get("sign", ""),  # 个性签名
                "ip_location": ip_location,  # IP属地
                "vip": 1 if member_info["vip"]["vipStatus"] == 1 else 0,  # 会员状态
                "face": member_info["avatar"],  # 头像URL
            },
        }
        return result
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"请求失败: {str(e)}"}
    except json.JSONDecodeError as e:
        return {"success": False, "message": f"JSON解析失败: {str(e)}"}
    except Exception as e:
        return {"success": False, "message": f"发生错误: {str(e)}"}


def generate_links(
    rpid,
    oid,
    type,
):
    link1 = ""
    link2 = f"https://www.bilibili.com/h5/comment/sub?oid={oid}&pageType={type}&root={rpid}"
    if type == 11:
        link1 = f"https://t.bilibili.com/{oid}?type=2#reply{rpid}"
    elif type == 14:
        link1 = f"https://t.bilibili.com/{oid}?type=256#reply{rpid}"
    elif type == 17:
        link1 = f"https://t.bilibili.com/{oid}#reply{rpid}"
    elif type == 1:
        link1 = f"https://www.bilibili.com/video/av{oid}/#reply{rpid}"
    return [link1, link2]

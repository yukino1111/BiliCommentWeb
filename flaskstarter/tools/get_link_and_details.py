import requests
import json
import time
import hashlib
import urllib.parse
from ..tools.config import COOKIE_PATH


def get_comment_details(oid: str, type: int, seek_rpid: str) -> dict:
    # 固定参数
    mode = 3
    plat = 1
    web_location = 1315875
    pagination_str = '{"offset":""}'

    # 获取时间戳用于签名
    wts = int(time.time())

    # 构造WBI签名
    code = (
        f"mode={mode}&oid={oid}&pagination_str={urllib.parse.quote(pagination_str)}&plat={plat}"
        f"&seek_rpid={seek_rpid}&type={type}&web_location={web_location}&wts={wts}"
        + "ea1db124af3c7062474693fa704f4ff8"  # WBI密钥
    )
    MD5 = hashlib.md5()
    MD5.update(code.encode("utf-8"))
    w_rid = MD5.hexdigest()

    # 构造请求URL
    url = (
        f"https://api.bilibili.com/x/v2/reply/wbi/main?oid={oid}&type={type}&mode={mode}"
        f"&pagination_str={urllib.parse.quote(pagination_str, safe=':')}&plat={plat}"
        f"&seek_rpid={seek_rpid}&web_location={web_location}&w_rid={w_rid}&wts={wts}"
    )

    # 获取cookie
    try:
        with open(COOKIE_PATH, "r") as f:
            cookie = f.read()
    except FileNotFoundError:
        print(f"Error: Cookie file not found at {COOKIE_PATH}.")
        cookie = ""

    # 构造请求头
    headers = {
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0",
    }

    try:
        # 发送请求
        response = requests.get(url=url, headers=headers, timeout=15)
        response.raise_for_status()
        data = json.loads(response.content.decode("utf-8"))

        if data.get("code") != 0:
            return {"success": False, "message": data.get("message", "API返回错误")}

        # 定义递归查找函数
        def find_comment(replies_list, target_rpid):
            if not replies_list:
                return None

            for reply in replies_list:
                # 检查当前评论
                if str(reply["rpid"]) == target_rpid:
                    return reply

                # 检查评论的回复
                if "replies" in reply and reply["replies"]:
                    found = find_comment(reply["replies"], target_rpid)
                    if found:
                        return found
            return None

        # 在返回的数据中查找指定rpid的评论
        comment_found = None

        # 首先检查根评论及其嵌套回复
        replies = data["data"].get("replies", [])
        comment_found = find_comment(replies, seek_rpid)

        # 如果没有找到，检查置顶评论及其嵌套回复
        if not comment_found and data["data"].get("top_replies"):
            comment_found = find_comment(data["data"]["top_replies"], seek_rpid)

        # 如果仍未找到，尝试通过二级评论API直接获取
        if not comment_found:
            # 检查 oid 是否为整数或字符串
            try:
                # 通过二级评论API获取指定评论
                second_url = f"https://api.bilibili.com/x/v2/reply/reply?oid={oid}&type={type}&root={seek_rpid}&ps=1&pn=1"
                second_response = requests.get(
                    url=second_url, headers=headers, timeout=10
                )
                second_response.raise_for_status()
                second_data = json.loads(second_response.content.decode("utf-8"))

                if second_data.get("code") == 0 and second_data["data"].get("root"):
                    comment_found = second_data["data"]["root"]
            except Exception as e:
                print(f"尝试通过二级评论API获取评论失败: {e}")

        # 如果没有找到指定的评论
        if not comment_found:
            return {"success": False, "message": f"未找到rpid为{seek_rpid}的评论"}

        # 提取评论信息
        member_info = comment_found["member"]

        # 提取IP属地
        ip_location = comment_found.get("reply_control", {}).get("location", "")
        if ip_location.startswith("IP属地："):
            ip_location = ip_location[5:]

        # 构造返回结果
        result = {
            "success": True,
            "comment_info": {
                "rpid": comment_found["rpid"],
                "oid": oid,
                "type": comment_found["type"],
                "mid": member_info["mid"],
                "name": member_info["uname"],
                "sex": member_info["sex"],
                "level": member_info["level_info"]["current_level"],
                "vip": 1 if member_info["vip"]["vipStatus"] == 1 else 0,
                "face": member_info["avatar"],
                "sign": member_info.get("sign", ""),
                "ip_location": ip_location,
                "content": comment_found["content"]["message"],
                "like_num": comment_found["like"],
                "time": comment_found["ctime"],
                "reply_num": 0,  # 默认为0
            },
        }

        # 获取回复数
        rereply_text = comment_found.get("reply_control", {}).get(
            "sub_reply_entry_text"
        )
        if rereply_text:
            import re

            match = re.findall(r"\d+", rereply_text)
            result["comment_info"]["reply_num"] = int(match[0]) if match else 0

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
    # 其他type不提供link1，link1将保持为空字符串
    return [link1, link2]

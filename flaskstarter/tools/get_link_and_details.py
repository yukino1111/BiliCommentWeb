import requests
import json
import time
import hashlib
import urllib.parse
from ..tools.config import COOKIE_PATH


def get_comment_details(oid: int, type: int, seek_rpid: int) -> dict:
    mode = 3
    plat = 1
    web_location = 1315875
    pagination_str = '{"offset":""}'

    wts = int(time.time())

    code = (
        f"mode={mode}&oid={oid}&pagination_str={urllib.parse.quote(pagination_str)}&plat={plat}"
        f"&seek_rpid={seek_rpid}&type={type}&web_location={web_location}&wts={wts}"
        + "ea1db124af3c7062474693fa704f4ff8"
    )
    MD5 = hashlib.md5()
    MD5.update(code.encode("utf-8"))
    w_rid = MD5.hexdigest()

    url = (
        f"https://api.bilibili.com/x/v2/reply/wbi/main?oid={oid}&type={type}&mode={mode}"
        f"&pagination_str={urllib.parse.quote(pagination_str, safe=':')}&plat={plat}"
        f"&seek_rpid={seek_rpid}&web_location={web_location}&w_rid={w_rid}&wts={wts}"
    )

    try:
        with open(COOKIE_PATH, "r") as f:
            cookie = f.read()
    except FileNotFoundError:
        print(f"Error: Cookie file not found at {COOKIE_PATH}.")
        cookie = ""

    headers = {
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0",
    }

    try:
        response = requests.get(url=url, headers=headers, timeout=15)
        response.raise_for_status()
        data = json.loads(response.content.decode("utf-8"))

        if data.get("code") != 0:
            return {"success": False, "message": data.get("message", "API返回错误")}

        def find_comment(replies_list, target_rpid):
            if not replies_list:
                return None

            for reply in replies_list:
                if str(reply["rpid"]) == target_rpid:
                    return reply

                if "replies" in reply and reply["replies"]:
                    found = find_comment(reply["replies"], target_rpid)
                    if found:
                        return found
            return None
        comment_found = None

        replies = data["data"].get("replies", [])
        comment_found = find_comment(replies, seek_rpid)

        if not comment_found and data["data"].get("top_replies"):
            comment_found = find_comment(data["data"]["top_replies"], seek_rpid)

        if not comment_found:
            try:
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

        if not comment_found:
            return {"success": False, "message": f"未找到rpid为{seek_rpid}的评论"}

        member_info = comment_found["member"]

        ip_location = comment_found.get("reply_control", {}).get("location", "")
        if ip_location.startswith("IP属地："):
            ip_location = ip_location[5:]

        result = {
            "success": True,
            "comment_info": {
                "mid": member_info["mid"],
                "name": member_info["uname"],
                "sex": member_info["sex"],
                "level": member_info["level_info"]["current_level"],
                "vip": 1 if member_info["vip"]["vipStatus"] == 1 else 0,
                "face": member_info["avatar"],
                "sign": member_info.get("sign", ""),
                "ip_location": ip_location,
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

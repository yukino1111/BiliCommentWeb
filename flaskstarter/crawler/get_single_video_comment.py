import re
import requests
import json
from urllib.parse import quote
import hashlib
import urllib
import time
from ..entity.bv import Bv
from ..entity.comment import Comment
from ..entity.user import User
from ..repository.comment_repository import CommentRepository
from ..repository.user_repository import UserRepository
from ..repository.bv_repository import BvRepository
from ..tools.config import *


class BilibiliCommentCrawler:

    def __init__(
        self,
        bv: str = None,
        is_second: bool = True,
        db_name: str = BILI_DB_PATH,
    ):
        self.bv = bv
        self.is_second = is_second
        self.cookie_path = COOKIE_PATH
        self.oid = None
        self.title = None
        self.next_pageID = ""
        self.count = 0

        self.comment_repo = CommentRepository(db_name)
        self.user_repo = UserRepository(db_name)
        self.bv_repo = BvRepository(db_name)

    def get_Header(self) -> dict:
        try:
            with open(self.cookie_path, "r") as f:
                cookie = f.read()
        except FileNotFoundError:
            print(
                f"Error: Cookie file not found at {self.cookie_path}. Please check the path and ensure you have a valid Bilibili cookie."
            )
            cookie = ""

        header = {
            "Cookie": cookie,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0",
        }
        return header

    def get_information(self) -> tuple[str, str]:
        resp = requests.get(
            f"https://www.bilibili.com/video/{self.bv}/",
            headers=self.get_Header(),
            timeout=10,
        )
        resp.raise_for_status()

        obj_oid = re.compile(f'"aid":(?P<id>.*?),"bvid":"{re.escape(self.bv)}"')
        match_oid = obj_oid.search(resp.text)
        if not match_oid:
            raise ValueError(
                f"无法从页面中提取 BV号: {self.bv} 对应的 OID。页面响应可能异常。"
            )
        self.oid = match_oid.group("id")

        obj_title = re.compile(r'<title data-vue-meta="true">(?P<title>.*?)</title>')
        match_title = obj_title.search(resp.text)
        if not match_title:
            self.title = f"视频 {self.bv}"
            print(f"Warning: 无法提取视频标题，使用默认值: {self.title}")
        else:
            self.title = (
                match_title.group("title").replace("_哔哩哔哩_bilibili", "").strip()
            )

        print(f"获取视频信息成功：OID={self.oid}, Title='{self.title}'")
        bv_obj = Bv(
            oid=self.oid,
            bid=self.bv,
            title=self.title,
        )
        self.bv_repo.add_or_update_bv(bv_obj)
        return self.oid, self.title

    def _parse_and_save_comment(
        self, raw_comment_data: dict, is_secondary: bool = False, parent_rpid: int = 0
    ):
        member_info = raw_comment_data["member"]
        user_mid = member_info["mid"]
        user_name = member_info["uname"]
        user_sex = member_info["sex"]
        user_face = member_info["avatar"]
        user_sign = member_info.get("sign", None)
        user_fans = None
        user_friend = None
        user_like_num = None
        user_vip_status = 1 if member_info["vip"]["vipStatus"] == 1 else 0

        user_obj = User(
            mid=user_mid,
            name=user_name,
            sex=user_sex,
            face=user_face,
            sign=user_sign,
            fans=user_fans,
            friend=user_friend,
            like_num=user_like_num,
            vip=user_vip_status,
        )

        self.user_repo.add_or_update_user(user_obj)

        rpid = raw_comment_data["rpid"]
        comment_parentid = (
            parent_rpid if is_secondary else raw_comment_data.get("parent", 0)
        )
        comment_rootid = (
            parent_rpid if is_secondary else raw_comment_data.get("root", 0)
        )
        comment_level = member_info["level_info"]["current_level"]
        comment_info = raw_comment_data["content"]["message"]
        comment_time = int(raw_comment_data["ctime"])
        rereply_text = raw_comment_data.get("reply_control", {}).get(
            "sub_reply_entry_text"
        )
        if rereply_text:
            match = re.findall(r"\d+", rereply_text)
            single_reply_num = int(match[0]) if match else 0
        else:
            single_reply_num = 0

        single_like_num = raw_comment_data["like"]
        ip_location = raw_comment_data.get("reply_control", {}).get("location", "")
        if ip_location.startswith("IP属地："):
            ip_location = ip_location[5:]
        type = int(raw_comment_data["type"])
        comment_obj = Comment(
            rpid=rpid,
            parentid=comment_parentid,
            rootid=comment_rootid,
            mid=user_mid,
            name=user_name,
            level=comment_level,
            sex=user_sex,
            information=comment_info,
            time=comment_time,
            single_reply_num=single_reply_num,
            single_like_num=single_like_num,
            sign=user_sign,
            ip_location=ip_location,
            vip=user_vip_status,
            face=user_face,
            oid=int(self.oid),
            type=type,
        )
        self.comment_repo.add_comment(comment_obj, overwrite=True)

    def start(self) -> bool:
        mode = 2
        plat = 1
        type = 1
        web_location = 1315875

        wts = int(time.time())

        if self.next_pageID != "":
            pagination_str = (
                '{"offset":"{\\"type\\":3,\\"direction\\":1,\\"Data\\":{\\"cursor\\":%d}}"}'
                % self.next_pageID
            )
        else:
            pagination_str = '{"offset":""}'

        code = (
            f"mode={mode}&oid={self.oid}&pagination_str={urllib.parse.quote(pagination_str)}&plat={plat}&seek_rpid=&type={type}&web_location={web_location}&wts={wts}"
            + "ea1db124af3c7062474693fa704f4ff8"
        )
        MD5 = hashlib.md5()
        MD5.update(code.encode("utf-8"))
        w_rid = MD5.hexdigest()

        url = f"https://api.bilibili.com/x/v2/reply/wbi/main?oid={self.oid}&type={type}&mode={mode}&pagination_str={urllib.parse.quote(pagination_str, safe=':')}&plat=1&seek_rpid=&web_location=1315875&w_rid={w_rid}&wts={wts}"

        try:
            response = requests.get(url=url, headers=self.get_Header(), timeout=15)
            response.raise_for_status()
            comment_data = json.loads(response.content.decode("utf-8"))
        except requests.exceptions.RequestException as e:
            print(f"请求评论API失败: {e}")
            return False
        except json.JSONDecodeError as e:
            print(
                f"解析评论JSON失败: {e}, 响应内容: {response.content.decode('utf-8', errors='ignore')[:200]}..."
            )
            return False

        if comment_data.get("code") != 0:
            print(f"API返回错误: {comment_data.get('message', '未知错误信息')}")
            if "wbi" in comment_data.get("message", "").lower():
                print(
                    "Hint: WBI签名可能已失效，请检查BilibiliCommentCrawler的WBI签名逻辑或更新Cookie。"
                )
            return False

        cursor_info = comment_data["data"]["cursor"]
        if cursor_info["mode"] == 3:
            print(f"评论爬取完成！总共爬取{self.count}条。")
            return False

        replies = comment_data["data"].get("replies", [])
        if not replies:
            print(f"当前页无评论数据 (可能已爬取完或API返回空).")
            return False

        for reply in replies:
            self.count += 1
            if self.count % 1000 == 0:
                print(f"已爬取 {self.count} 条评论，暂停 {20} 秒以避免反爬。")
                time.sleep(20)

            self._parse_and_save_comment(reply, is_secondary=False)

            single_reply_num = reply.get("reply_control", {}).get(
                "sub_reply_entry_text"
            )
            if single_reply_num:
                match = re.findall(r"\d+", single_reply_num)
                rereply_count = int(match[0]) if match else 0
            else:
                rereply_count = 0

            if self.is_second and rereply_count > 0:
                total_second_pages = (rereply_count // 10) + (
                    1 if rereply_count % 10 != 0 else 0
                )

                for page_num in range(1, total_second_pages + 1):
                    time.sleep(0.1)
                    second_url = f"https://api.bilibili.com/x/v2/reply/reply?oid={self.oid}&type=1&root={reply['rpid']}&ps=10&pn={page_num}&web_location=333.788"
                    try:
                        second_response = requests.get(
                            url=second_url, headers=self.get_Header(), timeout=10
                        )
                        second_response.raise_for_status()
                        second_comment_data = json.loads(
                            second_response.content.decode("utf-8")
                        )
                        if second_comment_data.get("code") != 0:
                            print(
                                f"API返回二级评论错误 (rpid={reply['rpid']}, page={page_num}): {second_comment_data.get('message', '未知错误')}"
                            )
                            break

                        second_replies = second_comment_data["data"].get("replies", [])
                        if not second_replies:
                            break

                        for second_reply in second_replies:
                            self.count += 1
                            if self.count % 1000 == 0:
                                print(
                                    f"已爬取 {self.count} 条评论，暂停 {20} 秒以避免反爬。"
                                )
                                time.sleep(20)
                            self._parse_and_save_comment(
                                second_reply,
                                is_secondary=True,
                                parent_rpid=reply["rpid"],
                            )
                    except requests.exceptions.RequestException as e:
                        print(
                            f"请求二级评论API失败 (rpid={reply['rpid']}, page={page_num}): {e}"
                        )
                        break
                    except json.JSONDecodeError as e:
                        print(
                            f"解析二级评论JSON失败 (rpid={reply['rpid']}, page={page_num}): {e}"
                        )
                        break

        self.next_pageID = cursor_info["next"]

        if self.next_pageID == 0:
            print(f"评论爬取完成！总共爬取{self.count}条。")
            return False
        else:
            time.sleep(0.5)
            print(f"当前爬取{self.count}条，正在准备下一页。")
            return True

    def crawl(self, bv: str = None) -> int:
        """
        开始爬取评论并保存到数据库。
        :param bv: 视频的BV号，如果不提供则使用初始化时的BV号
        :return: 爬取的评论总数量
        """
        if bv:
            self.bv = bv

        if not self.bv:
            raise ValueError("请提供视频BV号")

        print(f"开始爬取视频 BV号: {self.bv} 的评论。")

        try:
            self.get_information()
        except Exception as e:
            print(f"获取视频信息失败: {e}")
            return 0

        self.next_pageID = ""
        self.count = 0

        while True:
            should_continue = self.start()
            if not should_continue:
                break
        return self.count

import re
import requests
import json
from urllib.parse import quote
import hashlib
import urllib
import time
import datetime  # 替换 pandas.to_datetime
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
        db_name: str = BILI_DB_PATH,  # 新增数据库名参数
    ):
        self.bv = bv
        self.is_second = is_second
        self.cookie_path = COOKIE_PATH
        self.oid = None
        self.title = None
        self.next_pageID = ""
        self.count = 0  # 爬取到的评论总数

        # 数据库 Repository 实例
        self.comment_repo = CommentRepository(db_name)
        self.user_repo = UserRepository(db_name)
        self.bv_repo = BvRepository(db_name)

    # 获取B站的Header
    def get_Header(self) -> dict:
        """获取请求B站API所需的Header。"""
        try:
            with open(self.cookie_path, "r") as f:
                cookie = f.read()
        except FileNotFoundError:
            print(
                f"Error: Cookie file not found at {self.cookie_path}. Please check the path and ensure you have a valid Bilibili cookie."
            )
            # 返回一个不包含cookie的header，可能导致请求失败
            cookie = ""

        header = {
            "Cookie": cookie,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0",
            # 根据需要可以添加其他header，例如 Referer
            "Referer": f"https://www.bilibili.com/video/{self.bv}/",
        }
        return header

    # 通过bv号，获取视频的oid
    def get_information(self) -> tuple[str, str]:
        resp = requests.get(
            f"https://www.bilibili.com/video/{self.bv}/",
            headers=self.get_Header(),
            timeout=10,  # 设置超时时间
        )
        resp.raise_for_status()  # 检查HTTP响应状态码

        # 提取视频oid
        obj_oid = re.compile(f'"aid":(?P<id>.*?),"bvid":"{re.escape(self.bv)}"')
        match_oid = obj_oid.search(resp.text)
        if not match_oid:
            raise ValueError(
                f"无法从页面中提取 BV号: {self.bv} 对应的 OID。页面响应可能异常。"
            )
        self.oid = match_oid.group("id")

        # 提取视频的标题
        obj_title = re.compile(r'<title data-vue-meta="true">(?P<title>.*?)</title>')
        match_title = obj_title.search(resp.text)
        if not match_title:
            # 有些页面可能没有这个特定的title标签，可以尝试其他方式或者提供默认值
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
        # 提取用户数据
        member_info = raw_comment_data["member"]
        user_mid = member_info["mid"]
        user_name = member_info["uname"]
        user_sex = member_info["sex"]
        user_face = member_info["avatar"]
        user_sign = member_info.get("sign", None)  # 签名可能不存在
        user_fans = None  # API返回的member_info里通常没有fans, friend, like_num，这里留空或设置默认
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
        # 将用户信息存入数据库，mid存在则更新，不存在则插入
        self.user_repo.add_or_update_user(user_obj)

        # 提取评论数据
        rpid = raw_comment_data["rpid"]
        comment_parentid = (
            parent_rpid if is_secondary else raw_comment_data.get("parent", 0)
        )
        comment_rootid = (
            parent_rpid if is_secondary else raw_comment_data.get("root", 0)
        )  # 如果是一级评论，parentid通常是0
        # 如果是二级评论，parentid就是一级评论的rpid
        # 如果是一级评论，API返回的parent可能为0或其自身rpid，这里统一逻辑让它指向父评论ID
        comment_level = member_info["level_info"]["current_level"]
        comment_info = raw_comment_data["content"]["message"]
        # Unix 时间戳转换为 int 存储
        comment_time = int(raw_comment_data["ctime"])

        # 回复数
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
        # 如果IP是 "所在地："开头，则截取
        if ip_location.startswith("IP属地："):
            ip_location = ip_location[5:]
        type = int(raw_comment_data["type"])
        # 创建 Comment 实体
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
            oid=int(self.oid),  # oid是视频唯一ID
            type=type
        )
        # 将评论数据存入数据库，rpid存在则更新，不存在则插入
        self.comment_repo.add_comment(
            comment_obj, overwrite=True
        )  # 允许覆盖，因为评论内容可能在抓取时有更新，例如点赞数

    # 轮页爬取
    def start(self) -> bool:
        mode = 2
        plat = 1
        type = 1
        web_location = 1315875

        wts = int(time.time())  # 获取Unix时间戳 (秒)

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
            response.raise_for_status()  # 检查HTTP响应状态码
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
            # 如果是WBI签名错误，可能需要更新签名逻辑或cookie
            if "wbi" in comment_data.get("message", "").lower():
                print(
                    "Hint: WBI签名可能已失效，请检查BilibiliCommentCrawler的WBI签名逻辑或更新Cookie。"
                )
            return False

        cursor_info = comment_data["data"]["cursor"]
        if cursor_info["mode"] == 3:  # Mode 3 indicates no more pages
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

            # 二级评论
            single_reply_num = reply.get("reply_control", {}).get(
                "sub_reply_entry_text"
            )
            if single_reply_num:
                match = re.findall(r"\d+", single_reply_num)
                rereply_count = int(match[0]) if match else 0
            else:
                rereply_count = 0

            if self.is_second and rereply_count > 0:
                # B站二级评论每页10条
                total_second_pages = (rereply_count // 10) + (
                    1 if rereply_count % 10 != 0 else 0
                )

                # 只爬取前几页，避免大量回复的二级评论爬取时间过长，可以根据需要调整
                # 比如：只抓前 5 页的二级评论，如果回复数很多的话
                max_second_pages = min(
                    total_second_pages, 20
                )  # 假设最多爬取20页的二级评论

                for page_num in range(1, max_second_pages + 1):
                    # 避免对单个父评论的二级评论请求过于频繁
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
                            # 遇到错误，尝试下一页或直接跳过此根评论的后续二级评论
                            break

                        second_replies = second_comment_data["data"].get("replies", [])
                        if not second_replies:
                            break  # 当前页没有数据，说明已经爬完或请求过大

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
                        break  # 跳过此根评论的后续二级评论
                    except json.JSONDecodeError as e:
                        print(
                            f"解析二级评论JSON失败 (rpid={reply['rpid']}, page={page_num}): {e}"
                        )
                        break  # 跳过此根评论的后续二级评论

        # 更新下一页的pageID
        self.next_pageID = cursor_info["next"]

        if self.next_pageID == 0:
            print(f"评论爬取完成！总共爬取{self.count}条。")
            return False  # 表示爬取结束
        else:
            time.sleep(0.5)  # 适当暂停，避免反爬
            print(f"当前爬取{self.count}条，正在准备下一页。")
            return True  # 表示继续爬取

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
            self.get_information()  # 获取 OID 和 Title
        except Exception as e:
            print(f"获取视频信息失败: {e}")
            return 0  # 爬取终止

        # 重置爬取参数
        self.next_pageID = ""
        self.count = 0

        # 循环调用 start() 方法直到没有下一页
        while True:
            should_continue = self.start()
            if not should_continue:
                break
        return self.count

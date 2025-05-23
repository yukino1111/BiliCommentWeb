import requests
import json
import time
from typing import List, Optional, Dict, Any
from ..entity.comment import Comment
from ..repository.comment_repository import CommentRepository
from ..tools.config import *

class BilibiliUserCommentsCrawler:

    def __init__(self, db_name: str = BILI_DB_PATH):

        self.base_url = "https://api.aicu.cc/api/v3/search/getreply"
        self.comment_repo = CommentRepository(db_name)
        self.crawled_comment_count = 0
        self.page_size = 100  # 每页评论数量

    def _get_comments_page_from_api(
        self, uid: str, pn: int
    ) -> Optional[Dict[str, Any]]:
        params = {
            "uid": uid,
            "pn": pn,
            "ps": self.page_size,
            "mode": 0,  # 0表示按时间排序，1表示按点赞排序
            "keyword": "",  # 留空表示所有评论
        }
        try:
            response = requests.get(self.base_url, params=params, timeout=15)
            response.raise_for_status()  # 检查HTTP响应状态码
            data = response.json()

            if data.get("code") != 0:  # 检查API返回的业务状态码
                print(
                    f"API返回错误 for uid {uid}, page {pn}: {data.get('message', '未知错误')}"
                )
                return None

            return data.get("data")

        except requests.exceptions.RequestException as e:
            print(f"请求用户评论API失败 for uid {uid}, page {pn}: {e}")
            return None
        except json.JSONDecodeError as e:
            print(
                f"解析用户评论JSON失败 for uid {uid}, page {pn}: {e}, 响应内容: {response.text[:200]}..."
            )
            return None

    def _parse_and_save_comment(self, raw_comment_data: Dict[str, Any], user_id: int):
        try:
            rpid = int(raw_comment_data.get("rpid"))
            message = raw_comment_data.get("message", "")
            comment_time = int(raw_comment_data.get("time"))

            parent_data = raw_comment_data.get("parent", {})
            parentid = int(parent_data.get("parentid", 0)) if parent_data else 0
            rootid = int(parent_data.get("rootid", 0)) if parent_data else 0

            # dyn 字段包含 oid 和 type
            dyn_data = raw_comment_data.get("dyn", {})
            oid = int(dyn_data.get("oid", 0))  # 视频或内容的ID
            type= int(dyn_data.get("type", 0))  # 评论类型

            comment_obj = Comment(
                rpid=rpid,
                parentid=parentid,
                rootid=rootid,
                mid=user_id,
                information=message,
                time=comment_time,
                oid=oid,
                type=type,
            )
            self.comment_repo.add_mini_comment(comment_obj, overwrite=True)  # 允许覆盖

            self.crawled_comment_count += 1
            # print(f"  - 存储评论: rpid={rpid}, oid={oid}")
        except Exception as e:
            print(f"处理或存储评论数据失败 (rpid: {raw_comment_data.get('rpid')}): {e}")

    def crawl_user_all_comments(self, uid: int, delay_seconds: float = 0.5) -> int:
        if not uid:
            print("请提供用户ID。")
            return 0

        self.crawled_comment_count = 0
        current_page = 1
        is_end = False

        while not is_end:
            print(f"正在爬取用户 {uid} 的第 {current_page} 页评论...")
            data = self._get_comments_page_from_api(uid, current_page)

            if not data:
                print(f"获取用户 {uid} 第 {current_page} 页评论失败，停止爬取。")
                break

            replies = data.get("replies", [])
            if not replies:
                is_end = True  # 即使 is_end 为 false，如果 replies 为空也视为结束
                break

            for reply in replies:
                self._parse_and_save_comment(reply, uid)

            cursor_info = data.get("cursor", {})
            is_end = cursor_info.get("is_end", True)  # 默认如果is_end缺失则视为结束

            if not is_end:
                time.sleep(delay_seconds)  # 延迟，避免请求过快
                current_page += 1
            else:
                print(f"用户 {uid} 的评论已全部爬取。")

        print(
            f"用户 {uid} 的评论爬取完成。总计爬取 {self.crawled_comment_count} 条评论。"
        )
        return self.crawled_comment_count

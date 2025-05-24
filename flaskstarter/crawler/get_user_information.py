import requests
import json
import time
from typing import List, Optional
from ..entity.user import User
from ..repository.user_repository import UserRepository
from ..tools.config import *

class BilibiliUserCrawler:

    def __init__(self, db_name: str = BILI_DB_PATH):
        self.base_url = "https://worker.aicu.cc/api/bili/space"
        self.user_repo = UserRepository(db_name)
        self.crawled_count = 0

    def _get_user_data_from_api(self, mid: str) -> Optional[dict]:
        url = f"{self.base_url}?mid={mid}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("code") != 0:
                print(f"API返回错误 for mid {mid}: {data.get('message', '未知错误')}")
                return None

            return data.get("data")

        except requests.exceptions.RequestException as e:
            print(f"请求用户API失败 for mid {mid}: {e}")
            return None
        except json.JSONDecodeError as e:
            print(
                f"解析用户JSON失败 for mid {mid}: {e}, 响应内容: {response.text[:200]}..."
            )
            return None

    def crawl_user_info(self, mid: str) -> Optional[User]:
        raw_data = self._get_user_data_from_api(mid)
        if not raw_data:
            return None

        card_data = raw_data.get("card", {})
        like_num = raw_data.get("like_num")

        if not card_data:
            print(f"Warning: No 'card' data found for mid {mid}.")
            return None

        try:
            user_obj = User(
                mid=int(card_data.get("mid")),
                face=card_data.get("face"),
                fans=card_data.get("fans"),
                friend=card_data.get("friend"),
                name=card_data.get("name"),
                sex=card_data.get("sex"),
                sign=card_data.get("sign"),
                like_num=like_num,
                vip=1 if card_data.get("vip", {}).get("vipStatus") == 1 else 0,
            )
            print(f"成功获得用户信息: {user_obj.name} (mid: {user_obj.mid})")
            self.user_repo.add_or_update_user(user_obj)
            self.crawled_count += 1

            return user_obj
        except Exception as e:
            print(f"处理或存储用户 {mid} 数据失败: {e}")
            return None

    def crawl_users_batch(self, mids: List[str], delay_seconds: float = 0.5) -> int:
        if not mids:
            print("没有提供用户ID列表。")
            return 0

        print(f"开始批量爬取 {len(mids)} 个用户的信息...")
        successful_crawls = 0
        for i, mid in enumerate(mids):
            user = self.crawl_user_info(mid)
            if user:
                successful_crawls += 1

            if i < len(mids) - 1:
                time.sleep(delay_seconds)

            if (i + 1) % 10 == 0:
                print(f"已处理 {i + 1}/{len(mids)} 个用户。成功: {successful_crawls}")

        print(f"批量爬取完成。总计成功爬取 {successful_crawls} 个用户。")
        return successful_crawls

import re
import requests
import json
from urllib.parse import quote
import pandas as pd
import hashlib
import urllib
import time
import csv


class BilibiliCommentCrawler:
    def __init__(
        self,
        bv=None,
        is_second=True,
        cookie_path="./flaskstarter/assets/bili_cookie.txt",
    ):
        """
        初始化爬虫
        :param bv: 视频的BV号
        :param is_second: 是否爬取二级评论
        :param cookie_path: cookie文件路径
        """
        self.bv = bv
        self.is_second = is_second
        self.cookie_path = cookie_path
        self.oid = None
        self.title = None
        self.next_pageID = ""
        self.count = 0
        self.csv_writer = None

    # 获取B站的Header
    def get_Header(self):
        with open(self.cookie_path, "r") as f:
            cookie = f.read()
        header = {
            "Cookie": cookie,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0",
        }
        return header

    # 通过bv号，获取视频的oid
    def get_information(self):
        resp = requests.get(
            f"https://www.bilibili.com/video/{self.bv}/",
            headers=self.get_Header(),
        )
        # 提取视频oid
        obj = re.compile(f'"aid":(?P<id>.*?),"bvid":"{self.bv}"')
        self.oid = obj.search(resp.text).group("id")

        # 提取视频的标题
        obj = re.compile(r'<title data-vue-meta="true">(?P<title>.*?)</title>')
        self.title = obj.search(resp.text).group("title")

        return self.oid, self.title

    # 轮页爬取
    def start(self):
        # 参数
        mode = 2
        plat = 1
        type = 1
        web_location = 1315875

        # 获取当下时间戳
        wts = time.time()

        # 如果不是第一页
        if self.next_pageID != "":
            pagination_str = (
                '{"offset":"{\\"type\\":3,\\"direction\\":1,\\"Data\\":{\\"cursor\\":%d}}"}'
                % self.next_pageID
            )
        # 如果是第一页
        else:
            pagination_str = '{"offset":""}'

        # MD5加密
        code = (
            f"mode={mode}&oid={self.oid}&pagination_str={urllib.parse.quote(pagination_str)}&plat={plat}&seek_rpid=&type={type}&web_location={web_location}&wts={wts}"
            + "ea1db124af3c7062474693fa704f4ff8"
        )
        MD5 = hashlib.md5()
        MD5.update(code.encode("utf-8"))
        w_rid = MD5.hexdigest()

        url = f"https://api.bilibili.com/x/v2/reply/wbi/main?oid={self.oid}&type={type}&mode={mode}&pagination_str={urllib.parse.quote(pagination_str, safe=':')}&plat=1&seek_rpid=&web_location=1315875&w_rid={w_rid}&wts={wts}"
        comment = requests.get(url=url, headers=self.get_Header()).content.decode(
            "utf-8"
        )
        comment = json.loads(comment)
        if comment["data"]["cursor"]["mode"] == 3:
            print(f"评论爬取完成！总共爬取{self.count}条。")
            return False
        for reply in comment["data"]["replies"]:
            # 评论数量+1
            self.count += 1

            if self.count % 1000 == 0:
                time.sleep(20)

            # 上级评论ID
            parent = reply["parent"]
            # 评论ID
            rpid = reply["rpid"]
            # 用户ID
            uid = reply["mid"]
            # 用户名
            name = reply["member"]["uname"]
            # 用户等级
            level = reply["member"]["level_info"]["current_level"]
            # 性别
            sex = reply["member"]["sex"]
            # 头像
            avatar = reply["member"]["avatar"]
            # 是否是大会员
            if reply["member"]["vip"]["vipStatus"] == 0:
                vip = "否"
            else:
                vip = "是"
            # IP属地
            try:
                IP = reply["reply_control"]["location"][5:]
            except:
                IP = "未知"
            # 内容
            context = reply["content"]["message"]
            # 评论时间
            reply_time = pd.to_datetime(reply["ctime"], unit="s")
            # 相关回复数
            try:
                rereply = reply["reply_control"]["sub_reply_entry_text"]
                rereply = int(re.findall(r"\d+", rereply)[0])
            except:
                rereply = 0
            # 点赞数
            like = reply["like"]

            # 个性签名
            try:
                sign = reply["member"]["sign"]
            except:
                sign = ""

            # 写入CSV文件
            self.csv_writer.writerow(
                [
                    self.count,
                    parent,
                    rpid,
                    uid,
                    name,
                    level,
                    sex,
                    context,
                    reply_time,
                    rereply,
                    like,
                    sign,
                    IP,
                    vip,
                    avatar,
                ]
            )

            # 二级评论(如果开启了二级评论爬取，且该评论回复数不为0，则爬取该评论的二级评论)
            if self.is_second and rereply != 0:
                for page in range(1, rereply // 10 + 2):
                    second_url = f"https://api.bilibili.com/x/v2/reply/reply?oid={self.oid}&type=1&root={rpid}&ps=10&pn={page}&web_location=333.788"
                    second_comment = requests.get(
                        url=second_url, headers=self.get_Header()
                    ).content.decode("utf-8")
                    second_comment = json.loads(second_comment)
                    for second in second_comment["data"]["replies"]:
                        # 评论数量+1
                        self.count += 1
                        # 上级评论ID
                        parent = second["parent"]
                        # 评论ID
                        second_rpid = second["rpid"]
                        # 用户ID
                        uid = second["mid"]
                        # 用户名
                        name = second["member"]["uname"]
                        # 用户等级
                        level = second["member"]["level_info"]["current_level"]
                        # 性别
                        sex = second["member"]["sex"]
                        # 头像
                        avatar = second["member"]["avatar"]
                        # 是否是大会员
                        if second["member"]["vip"]["vipStatus"] == 0:
                            vip = "否"
                        else:
                            vip = "是"
                        # IP属地
                        try:
                            IP = second["reply_control"]["location"][5:]
                        except:
                            IP = "未知"
                        # 内容
                        context = second["content"]["message"]
                        # 评论时间
                        reply_time = pd.to_datetime(second["ctime"], unit="s")
                        # 相关回复数
                        try:
                            rereply = second["reply_control"]["sub_reply_entry_text"]
                            rereply = re.findall(r"\d+", rereply)[0]
                        except:
                            rereply = 0
                        # 点赞数
                        like = second["like"]
                        # 个性签名
                        try:
                            sign = second["member"]["sign"]
                        except:
                            sign = ""

                        # 写入CSV文件
                        self.csv_writer.writerow(
                            [
                                self.count,
                                parent,
                                second_rpid,
                                uid,
                                name,
                                level,
                                sex,
                                context,
                                reply_time,
                                rereply,
                                like,
                                sign,
                                IP,
                                vip,
                                avatar,
                            ]
                        )

        # 下一页的pageID
        self.next_pageID = comment["data"]["cursor"]["next"]
        # 判断是否是最后一页了
        if self.next_pageID == 0:
            print(f"评论爬取完成！总共爬取{self.count}条。")
            return False  # 表示爬取结束
        # 如果不是最后一页，则停0.5s（避免反爬机制）
        else:
            time.sleep(0.5)
            print(f"当前爬取{self.count}条。")
            return True  # 表示继续爬取

    def crawl(self, bv=None, output_file=None):
        """
        开始爬取评论
        :param bv: 视频的BV号，如果不提供则使用初始化时的BV号
        :param output_file: 输出文件名，如果不提供则使用视频标题+BV号
        :return: 爬取的评论数量
        """
        if bv:
            self.bv = bv

        if not self.bv:
            raise ValueError("请提供视频BV号")

        # 获取视频信息
        self.get_information()

        # 重置参数
        self.next_pageID = ""
        self.count = 0

        # 设置输出文件名
        if not output_file:
            output_file = f"./flaskstarter/comment/bv/{self.bv}.csv"

        # 创建CSV文件并写入表头
        with open(output_file, mode="w", newline="", encoding="utf-8-sig") as file:
            self.csv_writer = csv.writer(file)
            self.csv_writer.writerow(
                [
                    "序号",
                    "上级评论ID",
                    "评论ID",
                    "用户ID",
                    "用户名",
                    "用户等级",
                    "性别",
                    "评论内容",
                    "评论时间",
                    "回复数",
                    "点赞数",
                    "个性签名",
                    "IP属地",
                    "是否是大会员",
                    "头像",
                ]
            )

            # 开始爬取
            while self.start():
                pass

        return self.count, output_file


if __name__ == "__main__":
    # 示例用法
    # crawler = BilibiliCommentCrawler()
    # 爬取指定视频
    # crawler.crawl("BV1njEczKEYg")

    # 也可以在创建实例时指定BV号
    # crawler = BilibiliCommentCrawler(bv="BV1njEczKEYg", is_second=True)
    crawler = BilibiliCommentCrawler(bv="BV1tiEJzNEiy", is_second=True)

    crawler.crawl()

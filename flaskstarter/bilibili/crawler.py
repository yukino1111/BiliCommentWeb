# -*- coding: utf-8 -*-

import re
import requests
import json
import pandas as pd
import hashlib
import urllib
import time
import csv
import io
from datetime import datetime


class BilibiliCrawler:
    def __init__(self):
        with open('bili_cookie.txt','r') as f:
            cookie=f.read()
        self.header = {
            "Cookie": cookie,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        }

    def get_information(self, bv):
        """通过BV号获取视频的oid和标题"""
        resp = requests.get(
            f"https://www.bilibili.com/video/{bv}/", headers=self.header
        )
        # 提取视频oid
        obj = re.compile(f'"aid":(?P<id>.*?),"bvid":"{bv}"')
        oid = obj.search(resp.text).group("id")

        # 提取视频的标题
        obj = re.compile(r'<title data-vue-meta="true">(?P<title>.*?)</title>')
        title = obj.search(resp.text).group("title")

        return oid, title

    def crawl_comments(self, bv, is_second=True):
        """爬取B站视频评论并生成CSV内存文件"""
        oid, title = self.get_information(bv)
        next_pageID = ""
        count = 0

        # 创建CSV内存文件并写入表头
        output = io.StringIO()
        csv_writer = csv.writer(output)
        csv_writer.writerow(
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
                "IP属地",
                "是否是大会员",
            ]
        )

        # 爬取评论，最多爬取5页以避免超时
        max_pages = 5
        page_count = 0

        # while next_pageID != 0 and page_count < max_pages:
        while next_pageID != 0:
            page_count += 1
            next_pageID, count = self._crawl_page(
                bv, oid, next_pageID, count, csv_writer, is_second
            )

        return output.getvalue(), title

    def _crawl_page(self, bv, oid, pageID, count, csv_writer, is_second):
        """爬取单页评论"""
        # 参数
        mode = 2
        plat = 1
        type = 1
        web_location = 1315875

        # 获取当下时间戳
        wts = time.time()

        # 如果不是第一页
        if pageID != "":
            pagination_str = (
                '{"offset":"{\\"type\\":3,\\"direction\\":1,\\"Data\\":{\\"cursor\\":%d}}"}'
                % pageID
            )
        # 如果是第一页
        else:
            pagination_str = '{"offset":""}'

        # MD5加密
        code = (
            f"mode={mode}&oid={oid}&pagination_str={urllib.parse.quote(pagination_str)}&plat={plat}&seek_rpid=&type={type}&web_location={web_location}&wts={wts}"
            + "ea1db124af3c7062474693fa704f4ff8"
        )
        MD5 = hashlib.md5()
        MD5.update(code.encode("utf-8"))
        w_rid = MD5.hexdigest()

        url = f"https://api.bilibili.com/x/v2/reply/wbi/main?oid={oid}&type={type}&mode={mode}&pagination_str={urllib.parse.quote(pagination_str, safe=':')}&plat=1&seek_rpid=&web_location=1315875&w_rid={w_rid}&wts={wts}"

        try:
            response = requests.get(url=url, headers=self.header)
            comment = json.loads(response.content.decode("utf-8"))

            if (
                "data" in comment
                and "replies" in comment["data"]
                and comment["data"]["replies"]
            ):
                for reply in comment["data"]["replies"]:
                    # 评论数量+1
                    count += 1

                    # 上级评论ID
                    parent = reply.get("parent", "")
                    # 评论ID
                    rpid = reply.get("rpid", "")
                    # 用户ID
                    uid = reply.get("mid", "")
                    # 用户名
                    name = reply.get("member", {}).get("uname", "")
                    # 用户等级
                    level = (
                        reply.get("member", {})
                        .get("level_info", {})
                        .get("current_level", "")
                    )
                    # 性别
                    sex = reply.get("member", {}).get("sex", "")

                    # 是否是大会员
                    vip = (
                        "是"
                        if reply.get("member", {}).get("vip", {}).get("vipStatus", 0)
                        == 1
                        else "否"
                    )

                    # IP属地
                    try:
                        IP = (
                            reply.get("reply_control", {}).get("location", "")[5:]
                            or "未知"
                        )
                    except:
                        IP = "未知"

                    # 内容
                    context = reply.get("content", {}).get("message", "")

                    # 评论时间
                    try:
                        reply_time = datetime.fromtimestamp(reply.get("ctime", 0))
                    except:
                        reply_time = ""

                    # 相关回复数
                    try:
                        rereply_text = reply.get("reply_control", {}).get(
                            "sub_reply_entry_text", "0"
                        )
                        rereply = (
                            int(re.findall(r"\d+", rereply_text)[0])
                            if re.findall(r"\d+", rereply_text)
                            else 0
                        )
                    except:
                        rereply = 0

                    # 点赞数
                    like = reply.get("like", 0)

                    # 写入CSV文件
                    csv_writer.writerow(
                        [
                            count,
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
                            IP,
                            vip,
                        ]
                    )

                    # 二级评论
                    if is_second and rereply > 0:
                        self._crawl_second_comments(
                            oid, rpid, rereply, count, csv_writer
                        )

                # 下一页的pageID
                next_pageID = comment["data"]["cursor"].get("next", 0)
                return next_pageID, count
            else:
                return 0, count

        except Exception as e:
            # 出错则停止爬取
            print(f"爬取出错: {e}")
            return 0, count

    def _crawl_second_comments(self, oid, rpid, rereply, count, csv_writer):
        """爬取二级评论，最多爬取1页(10条)以避免超时"""
        try:
            second_url = f"https://api.bilibili.com/x/v2/reply/reply?oid={oid}&type=1&root={rpid}&ps=10&pn=1&web_location=333.788"
            second_resp = requests.get(url=second_url, headers=self.header)
            second_comment = json.loads(second_resp.content.decode("utf-8"))

            if (
                "data" in second_comment
                and "replies" in second_comment["data"]
                and second_comment["data"]["replies"]
            ):
                for second in second_comment["data"]["replies"]:
                    count += 1

                    parent = second.get("parent", "")
                    second_rpid = second.get("rpid", "")
                    uid = second.get("mid", "")
                    name = second.get("member", {}).get("uname", "")
                    level = (
                        second.get("member", {})
                        .get("level_info", {})
                        .get("current_level", "")
                    )
                    sex = second.get("member", {}).get("sex", "")

                    vip = (
                        "是"
                        if second.get("member", {}).get("vip", {}).get("vipStatus", 0)
                        == 1
                        else "否"
                    )

                    try:
                        IP = (
                            second.get("reply_control", {}).get("location", "")[5:]
                            or "未知"
                        )
                    except:
                        IP = "未知"

                    context = second.get("content", {}).get("message", "")

                    try:
                        reply_time = datetime.fromtimestamp(second.get("ctime", 0))
                    except:
                        reply_time = ""

                    like = second.get("like", 0)

                    csv_writer.writerow(
                        [
                            count,
                            parent,
                            second_rpid,
                            uid,
                            name,
                            level,
                            sex,
                            context,
                            reply_time,
                            0,
                            like,
                            IP,
                            vip,
                        ]
                    )

        except Exception as e:
            print(f"爬取二级评论出错: {e}")

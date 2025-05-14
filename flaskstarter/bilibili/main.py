import analyze
import get_all_bv
from get_single_video_comment import BilibiliCommentCrawler
import comment_merger
import os
import pandas as pd
import glob

if __name__ == "__main__":
    print("请选择获取评论模式：")
    print("0: 获取单个视频评论")
    print("1: 获取单个up主视频评论")
    get_mode = int(input("请输入模式（0/1）："))
    single_pos = ""
    # 创建基础目录结构
    bv_dir = os.path.join(".", "comment", "bv")
    up_dir = os.path.join(".", "comment", "up")

    if not os.path.exists(bv_dir):
        os.makedirs(bv_dir)
    if not os.path.exists(up_dir):
        os.makedirs(up_dir)

    if get_mode == 0:
        print("请输入视频BV号：")
        bv = input()
        print("是否开启二级评论爬取（默认开启）：")
        print("0: 否")
        print("1: 是")
        is_second = int(input())
        if is_second == 0:
            is_second = False
        else:
            is_second = True
        crawler = BilibiliCommentCrawler(bv=bv, is_second=is_second).crawl()
        single_pos = crawler[1]
        print(single_pos)

    elif get_mode == 1:
        print("请输入up主ID：")
        up_id = input()
        print("是否开启二级评论爬取（默认开启）：")
        print("0: 否")
        print("1: 是")
        is_second = int(input())
        if is_second == 0:
            is_second = False
        else:
            is_second = True

        # 获取UP主所有视频aid列表
        crawler = get_all_bv.GetInfo(up_id, headless=True)
        video_ids = crawler.next_page()
        print(f"共获取到 {len(video_ids)} 个视频，开始批量爬取评论...")
        for i, id in enumerate(video_ids):
            try:
                print(f"正在爬取第 {i+1}/{len(video_ids)} 个视频，ID: {id}")
                # B站可以通过av号访问视频，aid就是av号去掉前缀
                BilibiliCommentCrawler(id, is_second).crawl()
            except Exception as e:
                print(f"爬取视频 ID: {id} 时出错: {e}")

        single_pos = comment_merger.CommentMerger().merge_comments(
            video_ids, up_id
        )  # 可以指定输出目录

    else:
        print("输入错误")
        exit(1)

    print("请选择是否分析：")

    print("0: 否")
    print("1: 是")
    analyze_mode = int(input())

    if analyze_mode == 1:
        analyze.CommentAnalyzer(single_pos).run_all_analysis()

    elif analyze_mode == 0:
        print("程序退出")
        exit(0)
    else:
        print("输入错误")
        exit(1)

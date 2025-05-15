# -*- coding: utf-8 -*-

from flask import (
    Blueprint,
    render_template,
    flash,
    redirect,
    url_for,
    send_file,
    request,
)
from flask_login import login_required
import io
import os
from .forms import BVCrawlerForm, UIDCrawlerForm, ModeSelectForm
import pandas as pd

# from .crawler import BilibiliCrawler
from .get_single_video_comment import BilibiliCommentCrawler
from .get_all_bv import GetInfo
from .comment_merger import CommentMerger
from .analyze import CommentAnalyzer

bilibili = Blueprint("bilibili", __name__, url_prefix="/bilibili")


@bilibili.route("/select_mode", methods=["GET", "POST"])
@login_required
def select_mode():
    form = ModeSelectForm()
    if form.validate_on_submit():
        mode = form.mode.data
        return redirect(url_for(f"bilibili.{mode}_crawler"))
    return render_template("bilibili/select_mode.html", form=form)


@bilibili.route("/bv_crawler", methods=["GET", "POST"])
@login_required
def bv_crawler():
    form = BVCrawlerForm()
    if form.validate_on_submit():
        try:
            bv_input = form.bv.data
            is_second = form.is_second.data
            bv_list = [bv.strip() for bv in bv_input.split(",") if bv.strip()]
            if not bv_list:
                flash("请输入至少一个BV号", "warning")
                return render_template("bilibili/bv_crawler.html", form=form)
            successfully_crawled_bvs = []
            for i, bv in enumerate(bv_list):
                try:
                    print(f"正在爬取第 {i+1}/{len(bv_list)} 个BV号：{bv}")
                    crawler_success = BilibiliCommentCrawler(bv, is_second).crawl()
                    if crawler_success:
                        successfully_crawled_bvs.append(bv)
                except Exception as e:
                    print(f"爬取BV号 {bv} 时出错: {e}")
                    flash(f"爬取BV号 {bv} 时出错: {e}", "warning")
            if not successfully_crawled_bvs:
                flash("所有BV号的评论爬取都失败了，请检查BV号或稍后再试。", "danger")
                return render_template("bilibili/bv_crawler.html", form=form)
            first_bv = successfully_crawled_bvs[0]
            merged_filename_base = f"{first_bv}" # 文件名基础，加上“等”字
            if(len(successfully_crawled_bvs) > 1):
                merged_filename_base += "等"
            # flash("开始爬取，请稍等...", "info")
            CommentMerger().merge_comments(
                successfully_crawled_bvs, merged_filename_base
            )  # 可以指定输出目录
            return redirect(url_for("bilibili.upload_file", name=merged_filename_base))

        except Exception as e:
            flash(f"发生错误: {str(e)}", "danger")
    return render_template("bilibili/bv_crawler.html", form=form)


@bilibili.route("/uid_crawler", methods=["GET", "POST"])
@login_required
def uid_crawler():
    form = UIDCrawlerForm()
    if form.validate_on_submit():
        try:
            uid = form.uid.data
            is_second = form.is_second.data
            if not uid:
                flash("请输入UID", "warning")
                return render_template("bilibili/uid_crawler.html", form=form)
            # 获取UP主所有视频aid列表
            crawler = GetInfo(uid, headless=True)
            video_ids = crawler.next_page()
            print(f"共获取到 {len(video_ids)} 个视频，开始批量爬取评论...")
            for i, id in enumerate(video_ids):
                try:
                    print(f"正在爬取第 {i+1}/{len(video_ids)} 个视频，ID: {id}")
                    # B站可以通过av号访问视频，aid就是av号去掉前缀
                    BilibiliCommentCrawler(id, is_second).crawl()
                except Exception as e:
                    print(f"爬取视频 ID: {id} 时出错: {e}")

            CommentMerger().merge_comments(video_ids, uid)  # 可以指定输出目录

            # flash("开始爬取，请稍等...", "info")
            return redirect(url_for("bilibili.upload_file", name=uid))

        except Exception as e:
            flash(f"发生错误: {str(e)}", "danger")
    return render_template("bilibili/uid_crawler.html", form=form)


@bilibili.route("/upload/<name>")
@login_required
def upload_file(name):
    """处理爬取完成后的操作选择页面"""
    try:
        is_bv = is_bv_code(name)
        if is_bv:
            single_pos = "./flaskstarter/comment/bv/" + name + ".csv"
        else:
            single_pos = "./flaskstarter/comment/up/" + name + ".csv"

        # 检查文件是否存在
        import os

        if not os.path.exists(single_pos):
            flash("评论文件不存在", "danger")
            return redirect(url_for("bilibili.select_mode"))

        # 获取文件大小和行数
        file_size = os.path.getsize(single_pos) / 1024  # KB
        df = pd.read_csv(single_pos, encoding="utf-8")
        data_records_count = len(df) # len(DataFrame) 返回数据记录行数 (不含标题)

        # 渲染结果页面，提供下载和分析选项
        return render_template(
            "bilibili/upload_success.html",
            name=name,
            is_bv=is_bv,
            file_info={
                "size": round(file_size, 2),
                "line_count": data_records_count,  # 减去标题行
            },
        )
    except Exception as e:
        flash(f"处理失败: {str(e)}", "danger")
        return redirect(url_for("bilibili.select_mode"))


@bilibili.route("/download/<name>")
@login_required
def download_file(name):
    """直接下载CSV文件"""
    try:
        is_bv = is_bv_code(name)
        if is_bv:
            single_pos = "./comment/bv/" + name + ".csv"
        else:
            single_pos = "./comment/up/" + name + ".csv"
        # 设置文件名
        filename = f"{name}.csv"
        # 返回CSV文件供下载
        return send_file(
            single_pos, as_attachment=True, download_name=filename, mimetype="text/csv"
        )
    except Exception as e:
        flash(f"下载失败: {str(e)}", "danger")
        return redirect(url_for("bilibili.select_mode"))


@bilibili.route("/analyze/<name>")
@login_required
def analyze_file(name):
    """分析评论数据并展示结果"""
    try:
        # 确定文件路径
        is_bv = is_bv_code(name)
        if is_bv:
            csv_file = "./flaskstarter/comment/bv/" + name + ".csv"
        else:
            csv_file = "./flaskstarter/comment/up/" + name + ".csv"

        # 检查文件是否存在
        if not os.path.exists(csv_file):
            flash("评论文件不存在", "danger")
            return redirect(url_for("bilibili.select_mode"))

        # 输出目录（储存图片）
        output_dir = "./flaskstarter/static/image/" + name
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 初始化分析器
        analyzer = CommentAnalyzer(csv_file)
        analyzer.output_dir = output_dir  # 设置输出目录

        # 加载数据
        if not analyzer.load_data():
            flash("数据加载失败，请检查CSV文件格式", "danger")
            return redirect(url_for("bilibili.upload_file", name=name))

        # 运行分析并生成图表
        try:
            analyzer.analyze_ip_distribution()
        except Exception as e:
            print(f"IP分布分析失败: {e}")

        try:
            analyzer.analyze_vip_status()
        except Exception as e:
            print(f"大会员状态分析失败: {e}")

        try:
            analyzer.analyze_gender_distribution()
        except Exception as e:
            print(f"性别分布分析失败: {e}")

        try:
            analyzer.analyze_level_distribution()
        except Exception as e:
            print(f"用户等级分析失败: {e}")

        try:
            analyzer.analyze_comment_time_trend()
        except Exception as e:
            print(f"评论时间趋势分析失败: {e}")

        try:
            analyzer.analyze_comment_hour_distribution()
        except Exception as e:
            print(f"评论小时分布分析失败: {e}")

        try:
            analyzer.analyze_sentiment()
        except Exception as e:
            print(f"情感分析失败: {e}")

        try:
            analyzer.generate_wordcloud()
        except Exception as e:
            print(f"词云生成失败: {e}")

        # 收集生成的图表文件
        chart_files = {
            "ip_distribution": "user_ip_top10_distribution.png",
            "vip_status": "user_vip_status.png",
            "gender_distribution": "user_gender_distribution.png",
            "level_distribution": "user_level_distribution.png",
            "time_trend": "comment_time_trend.png",
            "hour_distribution": "comment_hour_distribution.png",
            "sentiment":"comment_sentiment_distribution.png",
            "wordcloud": "comment_wordcloud.png",
        }

        # 统计基本数据
        stats = {
            "total_comments": len(analyzer.df),
            "unique_users": (
                len(analyzer.df_unique_users)
                if analyzer.df_unique_users is not None
                else 0
            ),
            "file_size": os.path.getsize(csv_file) / 1024,  # KB
        }

        # 渲染分析结果页面
        return render_template(
            "bilibili/analysis_result.html",
            name=name,
            is_bv=is_bv,
            stats=stats,
            chart_files=chart_files,
            static_path=f"/static/image/{name}/",
        )
    except Exception as e:
        flash(f"分析失败: {str(e)}", "danger")
        return redirect(url_for("bilibili.upload_file", name=name))


def is_bv_code(input_string):
    # 转换为小写进行比较，实现大小写不敏感
    if input_string.lower().startswith("bv"):
        return 1
    else:
        return 0

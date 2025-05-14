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

from .forms import BVCrawlerForm, UIDCrawlerForm, ModeSelectForm

# from .crawler import BilibiliCrawler
from .get_single_video_comment import BilibiliCommentCrawler
from .get_all_bv import GetInfo
from .comment_merger import CommentMerger

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
            bv = form.bv.data
            is_second = form.is_second.data
            BilibiliCommentCrawler(bv=bv, is_second=is_second).crawl()
            flash("开始爬取，请稍等...", "info")
            return redirect(url_for("bilibili.upload_file", name=bv))

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

            CommentMerger().merge_comments(
                video_ids, uid
            )  # 可以指定输出目录

            flash("开始爬取，请稍等...", "info")
            return redirect(url_for("bilibili.upload_file", name=uid))

        except Exception as e:
            flash(f"发生错误: {str(e)}", "danger")
    return render_template("bilibili/uid_crawler.html", form=form)


# @bilibili.route("/download/<bv>")
# @login_required
# def download_comments(bv):
#     """处理爬取和下载CSV文件"""
#     is_second = request.args.get("is_second", "True").lower() == "true"

#     try:
#         crawler = BilibiliCommentCrawler(bv=bv, is_second=is_second).crawl()
#         single_pos = crawler[2]

#         # 设置文件名
#         filename = f"{bv}.csv"

#         # 返回CSV文件供下载
#         return send_file(
#             single_pos, as_attachment=True, download_name=filename, mimetype="text/csv"
#         )
#     except Exception as e:
#         flash(f"爬取失败: {str(e)}", "danger")
#         return redirect(url_for("bilibili.select_mode"))


@bilibili.route("/upload/<name>")
@login_required
def upload_file(name):
    """处理爬取和下载CSV文件"""
    try:
        is_bv = is_bv_code(name)
        if is_bv:
            single_pos ="./comment/bv/" + name + ".csv"
        else:
            single_pos = "./comment/up/" + name + ".csv"
        # 设置文件名
        filename = f"{name}.csv"
        # 返回CSV文件供下载
        return send_file(
            single_pos, as_attachment=True, download_name=filename, mimetype="text/csv"
        )
    except Exception as e:
        flash(f"上传失败: {str(e)}", "danger")


def is_bv_code(input_string):
    # 转换为小写进行比较，实现大小写不敏感
    if input_string.lower().startswith("bv"):
        return 1
    else:
        return 0

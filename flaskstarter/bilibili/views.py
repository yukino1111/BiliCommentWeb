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
import os

from flaskstarter.tools.get_link_and_details import generate_links
from .forms import BVCrawlerForm, UIDCrawlerForm, ModeSelectForm
import pandas as pd


from ..analyzer.analyze_comment import CommentAnalyzer
from ..crawler.get_single_video_comment import BilibiliCommentCrawler
from ..crawler.get_user_all_comment import BilibiliUserCommentsCrawler
from ..crawler.get_user_information import BilibiliUserCrawler
from ..database.db_manage import init_bilibili_db
from ..tools.config import *
from ..repository.comment_repository import CommentRepository
from ..tools.get_csv import (
    export_comments_by_oid_to_csv,
    export_comments_by_mid_to_csv_mini,
)
from ..repository.bv_repository import BvRepository
from ..tools import get_user_all_bv
import requests
from ..tools.get_link_and_details import get_comment_details

bilibili = Blueprint("bilibili", __name__, url_prefix="/bilibili")


@bilibili.route("/select_mode", methods=["GET", "POST"])
@login_required
def select_mode():
    for filename in os.listdir(IMAGE_DIR):
        if filename == ORIGIN_FACE_NAME:
            continue
        file_path = os.path.join(IMAGE_DIR, filename)
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except OSError as e:
                print(f"  错误：无法删除文件 '{filename}': {e}")

    if os.path.isfile(OUTPUT_CSV_PATH):
        try:
            os.remove(OUTPUT_CSV_PATH)
        except OSError as e:
            print(f"  错误：无法删除文件 '{filename}': {e}")

    form = ModeSelectForm()
    if form.validate_on_submit():
        mode = form.mode.data
        return redirect(url_for(f"bilibili.{mode}_crawler"))
    return render_template("bilibili/select_mode.html", form=form)


@bilibili.route("/bv_crawler", methods=["GET", "POST"])
@login_required
def bv_crawler():
    form = BVCrawlerForm()
    bv_repo = BvRepository(BILI_DB_PATH)
    if form.validate_on_submit():
        try:
            bv_input = form.bv.data
            is_second = form.is_second.data
            bv_list = [bv.strip() for bv in bv_input.split(",") if bv.strip()]
            if not bv_list:
                flash("请输入至少一个BV号", "warning")
                return render_template("bilibili/bv_crawler.html", form=form)
            for bv in bv_list:
                crawler = BilibiliCommentCrawler(bv=bv, is_second=is_second)
                crawler.crawl()
            try:
                video_oids = bv_repo.get_oids_by_bids(bv_list)
                export_comments_by_oid_to_csv(
                    output_filepath=OUTPUT_CSV_PATH,
                    oids=video_oids,
                    db_name=BILI_DB_PATH,
                )
            except Exception as e:
                print(f"失败: {e}")
                flash("爬取失败，请检查BV号或稍后再试。", "danger")
                return render_template("bilibili/bv_crawler.html", form=form)
            return redirect(url_for("bilibili.upload_file", name="bv"))
        except Exception as e:
            flash(f"发生错误: {str(e)}", "danger")
    return render_template("bilibili/bv_crawler.html", form=form)


@bilibili.route("/up_crawler", methods=["GET", "POST"])
@login_required
def up_crawler():
    bv_repo = BvRepository(BILI_DB_PATH)
    form = UIDCrawlerForm()
    if form.validate_on_submit():
        try:
            uid = form.uid.data
            is_second = form.is_second.data
            if not uid:
                flash("请输入UID", "warning")
                return render_template("bilibili/up_crawler.html", form=form)
            crawler = get_user_all_bv.GetInfo(uid, headless=True)
            video_ids = crawler.next_page()
            print(f"共获取到 {len(video_ids)} 个视频，开始批量爬取评论...")
            for bv in video_ids:
                crawler = BilibiliCommentCrawler(bv=bv, is_second=is_second)
                crawler.crawl()
            try:
                video_oids = bv_repo.get_oids_by_bids(video_ids)
                export_comments_by_oid_to_csv(
                    output_filepath=OUTPUT_CSV_PATH,
                    oids=video_oids,
                    db_name=BILI_DB_PATH,
                )
            except Exception as e:
                print(f"失败: {e}")
                flash("爬取失败，请检查UID或稍后再试。", "danger")
                return render_template("bilibili/up_crawler.html", form=form)
            return redirect(url_for("bilibili.upload_file", name="up"))
        except Exception as e:
            flash(f"发生错误: {str(e)}", "danger")
    return render_template("bilibili/up_crawler.html", form=form)


@bilibili.route("/uid_crawler", methods=["GET", "POST"])
@login_required
def uid_crawler():
    form = UIDCrawlerForm()
    if form.validate_on_submit():
        try:
            uid = form.uid.data
            mids = []
            mids.append(uid)
            if not uid:
                flash("请输入UID", "warning")
                return render_template("bilibili/up_crawler.html", form=form)
            crawler = BilibiliUserCrawler(db_name=BILI_DB_PATH)
            for single_mid in mids:
                crawler.crawl_user_info(single_mid)
            crawler = BilibiliUserCommentsCrawler(db_name=BILI_DB_PATH)
            for single_mid in mids:
                crawler.crawl_user_all_comments(single_mid, delay_seconds=0.5)
            try:
                export_comments_by_mid_to_csv_mini(
                    output_filepath=OUTPUT_CSV_PATH,
                    mids=mids,
                    db_name=BILI_DB_PATH,
                )
            except Exception as e:
                print(f"失败: {e}")
                flash("爬取失败，请检查UID或稍后再试。", "danger")
                return render_template("bilibili/uid_crawler.html", form=form)
            return redirect(url_for("bilibili.upload_file", name="uid"))
        except Exception as e:
            flash(f"发生错误: {str(e)}", "danger")
    return render_template("bilibili/uid_crawler.html", form=form)


@bilibili.route("/upload/<name>")
@login_required
def upload_file(name):
    """处理爬取完成后的操作选择页面"""
    try:
        if not os.path.exists(OUTPUT_CSV_PATH):
            flash("评论文件不存在", "danger")
            return redirect(url_for("bilibili.select_mode"))

        file_size = os.path.getsize(OUTPUT_CSV_PATH) / 1024
        df = pd.read_csv(OUTPUT_CSV_PATH, encoding="utf-8")
        data_records_count = len(df)
        page = request.args.get("page", 1, type=int)
        per_page = 10
        total_pages = (data_records_count + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, data_records_count)
        current_data = df.iloc[start_idx:end_idx]
        is_uid = name == "uid"
        comments = []
        for _, row in current_data.iterrows():
            comment_data = row.to_dict()
            rpid = int(comment_data.get("评论ID", 0))
            oid = int(comment_data.get("oid", 0))
            type = int(comment_data.get("type", 0))

            user_link, comment_link = generate_links(
                rpid,
                oid,
                type,
            )
            comment_data["user_link"] = user_link
            comment_data["comment_link"] = comment_link
            comments.append(comment_data)

        return render_template(
            "bilibili/upload_success.html",
            name=name,
            file_info={
                "size": round(file_size, 2),
                "line_count": data_records_count,
            },
            comments=comments,
            is_uid=is_uid,
            page=page,
            total_pages=total_pages,
        )

    except Exception as e:
        flash(f"处理失败: {str(e)}", "danger")
        return redirect(url_for("bilibili.select_mode"))


@bilibili.route("/download")
@login_required
def download_file():
    """直接下载CSV文件"""
    try:
        return send_file(
            OUTPUT_CSV_PATH1,
            as_attachment=True,
            download_name=OUTPUT_CSV_NAME,
            mimetype="text/csv",
        )
    except Exception as e:
        flash(f"下载失败: {str(e)}", "danger")
        return redirect(url_for("bilibili.select_mode"))


@bilibili.route("/analyze/<name>")
@login_required
def analyze_file(name):
    """分析评论数据并展示结果"""
    try:
        if not os.path.exists(OUTPUT_CSV_PATH):
            flash("评论文件不存在", "danger")
            return redirect(url_for("bilibili.select_mode"))
        analyzer = CommentAnalyzer(csv_path=OUTPUT_CSV_PATH)
        if name == "bv" or name == "up":
            analyzer.run_all_analysis()
            chart_files = {
                "ip_distribution": "user_ip_top10_distribution.png",
                "vip_status": "user_vip_status.png",
                "comment_comparison": "comment_radar_chart.png",
                "gender_distribution": "user_gender_distribution.png",
                "level_distribution": "user_level_distribution.png",
                "time_trend": "comment_time_trend.png",
                "hour_distribution": "comment_hour_distribution.png",
                "sentiment": "comment_sentiment_distribution.png",
                "wordcloud": "comment_wordcloud.png",
            }
            stats = {
                "total_comments": len(analyzer.df),
                "unique_users": (
                    len(analyzer.df_unique_users)
                    if analyzer.df_unique_users is not None
                    else 0
                ),
                "file_size": os.path.getsize(OUTPUT_CSV_PATH) / 1024,
            }
            return render_template(
                "bilibili/comment_analysis_result.html",
                name=name,
                stats=stats,
                chart_files=chart_files,
                static_path=STATIC_IMAGE_DIR,
            )
        elif name == "uid":
            analyzer.run_mini_analysis()
            chart_files = {
                "time_trend": "comment_time_trend.png",
                "hour_distribution": "comment_hour_distribution.png",
                "sentiment": "comment_sentiment_distribution.png",
                "wordcloud": "comment_wordcloud.png",
            }
            user_mid = None
            if analyzer.df is not None and not analyzer.df.empty:
                user_mid = (
                    int(analyzer.df["用户ID"].iloc[0])
                    if "用户ID" in analyzer.df.columns
                    else None
                )
            user_detail = None
            if user_mid:
                comment_repo = CommentRepository(db_name=BILI_DB_PATH)
                latest_comment = comment_repo.get_latest_comment_by_mid(user_mid)
                if latest_comment:
                    user_detail = get_comment_details(
                        latest_comment["oid"],
                        latest_comment["type"],
                        latest_comment["rpid"],
                    )
            try:
                response = requests.get(
                    user_detail["comment_info"]["face"], stream=True
                )
                response.raise_for_status()
                print(USER_FACE_PATH)
                with open(USER_FACE_PATH, "wb") as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)
                user_detail["comment_info"]["face"] = USER_FACE_NAME
            except requests.exceptions.RequestException as e:
                user_detail["comment_info"]["face"] = ORIGIN_FACE_NAME
            stats = {
                "total_comments": len(analyzer.df),
                "unique_users": (
                    len(analyzer.df_unique_users)
                    if analyzer.df_unique_users is not None
                    else 0
                ),
                "file_size": os.path.getsize(OUTPUT_CSV_PATH) / 1024,
            }
            print(f"userdata{user_detail}")
            return render_template(
                "bilibili/uid_analysis_result.html",
                name=name,
                stats=stats,
                chart_files=chart_files,
                static_path=STATIC_IMAGE_DIR,
                user_detail=user_detail,
            )
    except Exception as e:
        flash(f"分析失败: {str(e)}", "danger")
        return redirect(url_for("bilibili.upload_file", name=name))

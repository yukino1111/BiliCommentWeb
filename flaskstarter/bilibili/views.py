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

from .forms import BilibiliCrawlerForm
from .crawler import BilibiliCrawler

bilibili = Blueprint("bilibili", __name__, url_prefix="/bilibili")


@bilibili.route("/crawler", methods=["GET", "POST"])
@login_required
def crawler():
    """B站评论爬虫表单页面"""
    form = BilibiliCrawlerForm()

    if form.validate_on_submit():
        try:
            bv = form.bv.data
            is_second = form.is_second.data

            flash("开始爬取，请稍等...", "info")
            return redirect(
                url_for("bilibili.download_comments", bv=bv, is_second=is_second)
            )

        except Exception as e:
            flash(f"发生错误: {str(e)}", "danger")

    return render_template("bilibili/crawler.html", form=form)


@bilibili.route("/download/<bv>")
@login_required
def download_comments(bv):
    """处理爬取和下载CSV文件"""
    is_second = request.args.get("is_second", "True").lower() == "true"

    try:
        crawler = BilibiliCrawler()
        csv_content, title = crawler.crawl_comments(bv, is_second)

        # 创建一个字节流，包含CSV内容
        csv_bytes = csv_content.encode("utf-8-sig")  # 使用带BOM的UTF-8编码
        mem_file = io.BytesIO(csv_bytes)

        # 文件名中去除特殊字符
        safe_title = "".join(c for c in title[:20] if c.isalnum() or c in " _-").strip()
        if not safe_title:
            safe_title = bv

        # 设置文件名
        filename = f"{safe_title}_评论.csv"

        # 返回CSV文件供下载
        return send_file(
            mem_file, as_attachment=True, download_name=filename, mimetype="text/csv"
        )
    except Exception as e:
        flash(f"爬取失败: {str(e)}", "danger")
        return redirect(url_for("bilibili.crawler"))

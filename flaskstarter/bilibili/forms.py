from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField
from wtforms.validators import InputRequired, Length, Regexp


class BilibiliCrawlerForm(FlaskForm):
    bv = StringField(
        "B站视频BV号",
        [
            InputRequired(),
            Length(min=12, max=12),
            Regexp(
                r"^BV[a-zA-Z0-9]{10}$",
                message="请输入正确格式的BV号，例如：BV1awjwzmEao",
            ),
        ],
    )
    is_second = BooleanField("爬取二级评论", default=True)
    submit = SubmitField("开始爬取")

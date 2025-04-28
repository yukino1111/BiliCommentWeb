# -*- coding: utf-8 -*-
"""
    Common utilities to be used in application
"""

import os

import datetime


# Instance folder path, to keep stuff aware from flask app.
# INSTANCE_FOLDER_PATH = os.path.join('/tmp', 'flaskstarter-instance')
# INSTANCE_FOLDER_PATH = "E:/Users/lenovo/Desktop/flask-starter-main/instance"
basedir = os.path.abspath(os.path.dirname(__file__))
# 在项目根目录下创建一个 'tmp' 文件夹
tmp_folder = os.path.join(basedir, "tmp")
# 将实例文件夹路径设置为项目根目录下的 'tmp/flaskstarter-instance'
INSTANCE_FOLDER_PATH = os.path.join(tmp_folder, "flaskstarter-instance")

# Form validation

NAME_LEN_MIN = 4
NAME_LEN_MAX = 25

PASSWORD_LEN_MIN = 6
PASSWORD_LEN_MAX = 16


# Model
STRING_LEN = 64


def get_current_time():
    return datetime.datetime.utcnow()


def pretty_date(dt, default=None):
    # Returns string representing "time since" eg 3 days ago, 5 hours ago etc.

    if default is None:
        default = 'just now'

    now = datetime.datetime.utcnow()
    diff = now - dt

    periods = (
        (diff.days / 365, 'year', 'years'),
        (diff.days / 30, 'month', 'months'),
        (diff.days / 7, 'week', 'weeks'),
        (diff.days, 'day', 'days'),
        (diff.seconds / 3600, 'hour', 'hours'),
        (diff.seconds / 60, 'minute', 'minutes'),
        (diff.seconds, 'second', 'seconds'),
    )

    for period, singular, plural in periods:

        if not period:
            continue

        if int(period) >= 1:
            if int(period) > 1:
                return u'%d %s ago' % (period, plural)
            return u'%d %s ago' % (period, singular)

    return default

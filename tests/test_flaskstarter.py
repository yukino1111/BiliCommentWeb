# -*- coding: utf-8 -*-

import pytest

from flask_login import current_user
from flaskstarter import create_app
from flaskstarter.extensions import db
from flaskstarter.user import Users, USER, ACTIVE


@pytest.fixture
def client():
    app = create_app()

    app.config["TESTING"] = True
    app.testing = True

    client = app.test_client()
    yield client


def test_home_page(client):
    response = client.get("/")
    assert b"Let's start with Python & Flask" in response.data


def test_bilibili_crawler_page_redirect_if_not_logged_in(client):
    """测试未登录访问B站爬虫页面会被重定向到登录页"""
    response = client.get("/bilibili/crawler", follow_redirects=False)
    assert response.status_code == 302  # 应该重定向到登录
    assert "/login" in response.location

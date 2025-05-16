# -*- coding: utf-8 -*-

from sqlalchemy.orm.mapper import configure_mappers

from flaskstarter import create_app
from flaskstarter.extensions import db
from flaskstarter.user import Users, ADMIN, USER, ACTIVE

from flaskstarter.utils import INSTANCE_FOLDER_PATH

application = create_app()


@application.cli.command("initdb")
def initdb():
    """Init/reset database."""
    print(f"INSTANCE_FOLDER_PATH: " + INSTANCE_FOLDER_PATH)
    db.drop_all()
    configure_mappers()
    db.create_all()

    admin = Users(name='Admin Flask-Starter',
                  email=u'admin@your-mail.com',
                  password=u'adminpassword',
                  role_code=ADMIN,
                  status_code=ACTIVE)

    db.session.add(admin)

    for i in range(1, 2):
        user = Users(name='Demo User',
                     email=u'demo@your-mail.com',
                     password=u'demopassword',
                     role_code=USER,
                     status_code=ACTIVE)
        db.session.add(user)

    db.session.commit()

    print("Database initialized with 2 users (admin, demo)")

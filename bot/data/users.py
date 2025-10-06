from datetime import datetime as dt
import sqlalchemy
from .db_session import SqlAlchemyBase


class User(SqlAlchemyBase):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    modified_date = sqlalchemy.Column(sqlalchemy.DateTime, default=dt.now)
    task_type = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
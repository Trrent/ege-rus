import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase


class Task(SqlAlchemyBase):
    __tablename__ = 'tasks'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    type = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    question = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    options = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    explanation = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    correct_option = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    rule_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("rules.id"), nullable=True)

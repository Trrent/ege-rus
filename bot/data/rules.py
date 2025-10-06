import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase


class Rule(SqlAlchemyBase):
    __tablename__ = 'rules'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    rule = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    tasks = orm.relationship('Task', backref='rule')
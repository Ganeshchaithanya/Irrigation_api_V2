"""
SQLAlchemy declarative base.
All ORM models must import from here.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass

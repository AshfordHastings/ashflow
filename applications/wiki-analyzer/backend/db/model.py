from sqlalchemy import String, Integer, Column, ForeignKey, Table, Float, DateTime, Date
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class PageViewCounts(Base):
    __tablename__ = "pageview_counts"
    pagename: Mapped[str] = mapped_column(nullable=False)
    pageviewcount: Mapped[int] = mapped_column(nullable=False)
    date: Mapped[datetime] = mapped_column(nullable=False)

class DailyPageViewCounts(Base):
    __tablename__ = "daily_pageview_counts"
    pagename: Mapped[str] = mapped_column(nullable=False, primary_key=True)
    dailyviews: Mapped[int] = mapped_column(nullable=False)
    date: Mapped[Date] = mapped_column(nullable=False, primary_key=True)

class WikiPage(Base): 
    __tablename__ = "wiki_page"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)

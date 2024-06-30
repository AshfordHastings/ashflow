
from sqlalchemy.orm import Session 
from db.model import WikiPage, PageViewCounts, DailyPageViewCounts


def get_wiki_pages(session: Session):
    return session.query(WikiPage).all()

def delete_wiki_page(session: Session, page_id: int):
    page = session.query(WikiPage).filter(WikiPage.id == page_id).first()
    if not page:
        raise ValueError(f"Page with id {page_id} not found.")
    session.delete(page)
    session.commit()

def get_page_view_counts(session: Session):
    return session.query(PageViewCounts).all()

def get_daily_page_view_counts(session: Session):
    return session.query(DailyPageViewCounts).all()

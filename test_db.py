from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.config import settings
from app.models import Article

engine = create_engine(settings.sync_database_url)
with Session(engine) as session:
    articles = session.scalars(select(Article).order_by(Article.created_at.desc()).limit(5)).all()
    for a in articles:
        print(f"Title: {a.title}")
        print(f"Is Source: {a.is_source}")
        print(f"Body: {a.body[:300]}")
        print("---")

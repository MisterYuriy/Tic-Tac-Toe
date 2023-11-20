import sqlalchemy as db
from sqlalchemy.orm import sessionmaker

engine = db.create_engine("sqlite:///app.db")
Session = sessionmaker(engine)

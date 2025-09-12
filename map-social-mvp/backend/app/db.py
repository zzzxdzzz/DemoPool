from sqlmodel import SQLModel, create_engine, Session
import os

sqlite_path = os.getenv("SQLITE_PATH", "./app/data.db")
engine = create_engine(f"sqlite:///{sqlite_path}", connect_args={"check_same_thread": False})

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

from contextlib import contextmanager
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime, ForeignKey,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from .config import settings

engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    source_type = Column(String, nullable=False, default="git")  # "git" | "local"
    repo_url = Column(String, nullable=False)  # git URL, or absolute local path
    branch = Column(String, default="main")  # unused for source_type=="local"
    llm_provider = Column(String, nullable=False)  # "azure_openai" | "gemini"
    llm_config = Column(Text)  # JSON blob (per-project overrides, optional)
    last_commit_sha = Column(String)
    status = Column(String, default="created")  # created | analyzing | ready | error
    status_detail = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    files = relationship("FileRecord", back_populates="project", cascade="all, delete-orphan")
    docs = relationship("DocPage", back_populates="project", cascade="all, delete-orphan")


class FileRecord(Base):
    """Tracks the hash + summary of every source file we've analyzed."""
    __tablename__ = "files"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    path = Column(String, nullable=False)  # relative to repo root
    sha256 = Column(String, nullable=False)
    summary = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="files")


class DocPage(Base):
    """One markdown page in the wiki. `slug` is its filename without .md."""
    __tablename__ = "doc_pages"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    slug = Column(String, nullable=False)  # e.g. "overview", "architecture", "modules/backend-app"
    title = Column(String, nullable=False)
    kind = Column(String, nullable=False)  # "overview" | "architecture" | "module"
    source_paths = Column(Text)  # JSON list of repo-relative paths feeding this page
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="docs")


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope():
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()

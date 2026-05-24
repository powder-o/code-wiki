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
    runs = relationship("RunEvent", cascade="all, delete-orphan",
                        primaryjoin="Project.id == RunEvent.project_id")
    code_symbols = relationship("CodeSymbol", cascade="all, delete-orphan",
                                primaryjoin="Project.id == CodeSymbol.project_id")
    code_calls = relationship("CodeCall", cascade="all, delete-orphan",
                              primaryjoin="Project.id == CodeCall.project_id")
    code_edges = relationship("CodeEdge", cascade="all, delete-orphan",
                              primaryjoin="Project.id == CodeEdge.project_id")


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


class RunEvent(Base):
    """One row per successful analyze/update run. Drives the activity sparkline."""
    __tablename__ = "run_events"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    kind = Column(String, nullable=False)  # "initial" | "update"
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class CodeSymbol(Base):
    """A callable/class/component symbol defined in a source file."""
    __tablename__ = "code_symbols"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    file_path = Column(String, nullable=False)
    name = Column(String, nullable=False)
    kind = Column(String, nullable=False)
    language = Column(String, nullable=False)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    signature = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class CodeCall(Base):
    """A call/reference extracted from a source file."""
    __tablename__ = "code_calls"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    file_path = Column(String, nullable=False)
    name = Column(String, nullable=False)
    language = Column(String, nullable=False)
    start_line = Column(Integer, nullable=False)
    context = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class CodeEdge(Base):
    """A resolved file-to-file relationship: source defines, target calls."""
    __tablename__ = "code_edges"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    source_path = Column(String, nullable=False)
    target_path = Column(String, nullable=False)
    symbols_json = Column(Text, nullable=False)
    weight = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


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

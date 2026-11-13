import os
from pathlib import Path
from sqlalchemy import create_engine, String, Integer, ForeignKey, JSON, UniqueConstraint, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
ROOT=Path(__file__).resolve().parents[2]
DB_URL=os.getenv('SKILLGRAPH_DB',f'sqlite:///{ROOT / "data/skillgraph.db"}')
engine=create_engine(DB_URL,connect_args={'check_same_thread':False})
@event.listens_for(engine,'connect')
def foreign_keys(conn,_):
    conn.execute('PRAGMA foreign_keys=ON')
Session=sessionmaker(engine,expire_on_commit=False)
class Base(DeclarativeBase): pass
class Student(Base):
    __tablename__='students'
    id:Mapped[int]=mapped_column(primary_key=True)
    name:Mapped[str]=mapped_column(String(100))
    course:Mapped[str]=mapped_column(default='B.Tech CSE')
    year:Mapped[int]=mapped_column(default=3)
    interests:Mapped[list]=mapped_column(JSON,default=list)
    projects:Mapped[str]=mapped_column(default='')
    demo:Mapped[bool]=mapped_column(default=False,index=True)
class Catalog(Base):
    __tablename__='catalog'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    kind:Mapped[str]=mapped_column(index=True)
    payload:Mapped[dict]=mapped_column(JSON)
class StudentSkill(Base):
    __tablename__='student_skills'
    student_id:Mapped[int]=mapped_column(ForeignKey('students.id',ondelete='CASCADE'),primary_key=True)
    skill_id:Mapped[str]=mapped_column(ForeignKey('catalog.id'),primary_key=True)
    proficiency:Mapped[int]=mapped_column(Integer)
class Progress(Base):
    __tablename__='progress'
    student_id:Mapped[int]=mapped_column(ForeignKey('students.id',ondelete='CASCADE'),primary_key=True)
    occupation_id:Mapped[str]=mapped_column(ForeignKey('catalog.id'),primary_key=True)
    skill_id:Mapped[str]=mapped_column(ForeignKey('catalog.id'),primary_key=True)
    completed:Mapped[bool]=mapped_column(default=False)
class ImportLog(Base):
    __tablename__='imports'
    id:Mapped[int]=mapped_column(primary_key=True)
    payload:Mapped[dict]=mapped_column(JSON)
Base.metadata.create_all(engine)

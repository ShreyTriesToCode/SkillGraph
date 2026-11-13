import json, re
from contextlib import asynccontextmanager
from typing import Annotated
import pandas as pd
from io import BytesIO
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select, delete
from rdflib.plugins.sparql.parser import parseQuery
from .store import Session, Student, StudentSkill, Progress, ImportLog
from .service import *
from .importers import student_csv
@asynccontextmanager
async def lifespan(app):
    seed();MODEL.fit();yield
app=FastAPI(title='SkillGraph API',version='1.0.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=['http://127.0.0.1:5173','http://localhost:5173'],allow_methods=['*'],allow_headers=['*'])
class ProfileIn(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=1,max_length=100)
    course:str=Field(default='B.Tech CSE',max_length=120)
    year:int=Field(default=3,ge=1,le=6)
    skills:dict[str,int]=Field(default_factory=dict,max_length=200)
    interests:list[str]=Field(default_factory=list,max_length=30)
    projects:str=Field(default='',max_length=5000)
class Completion(BaseModel):
    completed:bool
    acquired:bool=False
    proficiency:int=Field(default=3,ge=1,le=5)
class Query(BaseModel):
    query:str=Field(max_length=5000)
@app.exception_handler(KeyError)
async def key_error(_,exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=404,content={'detail':str(exc.args[0])})
@app.get('/api/health')
def health():return {'status':'ok'}
@app.get('/api/catalog')
def get_catalog():
    sk,oc=catalog();return {'skills':list(sk.values()),'occupations':list(oc.values())}
@app.get('/api/students')
def students():
    with Session() as db:ids=list(db.scalars(select(Student.id).order_by(Student.id)))
    return [profile(i) for i in ids]
@app.get('/api/students/{sid}')
def student(sid:int):return profile(sid)
def save_profile(p:ProfileIn,sid=None):
    skills,_=catalog();norm={}
    for s,level in p.skills.items():
        key=normalize(s,skills)
        if not key:raise HTTPException(422,'Unknown skill: '+s)
        if isinstance(level,bool) or not 1<=level<=5:raise HTTPException(422,'Proficiency must be 1–5')
        norm[key]=max(level,norm.get(key,0))
    with Session() as db:
        st=db.get(Student,sid) if sid else Student()
        if sid and st is None:raise KeyError('Student not found')
        for key in ['name','course','year','interests','projects']:setattr(st,key,getattr(p,key))
        db.add(st);db.flush();sid=st.id
        db.execute(delete(StudentSkill).where(StudentSkill.student_id==sid))
        for key,level in norm.items():db.add(StudentSkill(student_id=sid,skill_id=key,proficiency=level))
        db.commit()
    return profile(sid)
@app.post('/api/students',status_code=201)
def create(p:ProfileIn):return save_profile(p)
@app.put('/api/students/{sid}')
def update(sid:int,p:ProfileIn):profile(sid);return save_profile(p,sid)
@app.get('/api/students/{sid}/recommendations')
def recommendations(sid:int):return {'recommendations':rank(profile(sid)),'model':MODEL.metadata,'weights':CFG}
@app.get('/api/students/{sid}/gap')
def get_gap(sid:int,occupation:str):return gap(profile(sid),occupation)
@app.get('/api/students/{sid}/roadmap')
def get_roadmap(sid:int,occupation:str):return roadmap(profile(sid),occupation)
@app.put('/api/students/{sid}/progress')
def progress(sid:int,occupation:str,skill:str,p:Completion):
    st=profile(sid);sk,oc=catalog()
    if occupation not in oc or skill not in sk:raise KeyError('Unknown occupation or skill')
    valid={x['skill'] for x in roadmap(st,occupation)}|set(st['skills'])
    if skill not in valid:raise HTTPException(422,'Skill is not part of this roadmap')
    with Session() as db:
        db.merge(Progress(student_id=sid,occupation_id=occupation,skill_id=skill,completed=p.completed))
        if p.acquired and p.completed:db.merge(StudentSkill(student_id=sid,skill_id=skill,proficiency=p.proficiency))
        db.commit()
    return {'student':profile(sid),'roadmap':roadmap(profile(sid),occupation)}
@app.post('/api/demo/reset')
def reset():seed(reset=True);return students()
@app.get('/api/graph')
def graph(sid:int,occupation:str):return {'elements':subgraph(profile(sid),occupation),'triple_count':len(build_graph()),'queries':QUERIES}
@app.get('/api/graph/triples')
def triples():return Response(build_graph().serialize(format='turtle'),media_type='text/turtle')
@app.post('/api/graph/query')
def query(p:Query):
    # Only local, non-federated SELECT. Never allow SPARQL network/file access.
    if re.search(r'\b(SERVICE|LOAD|FROM|INSERT|DELETE|CLEAR|CREATE|DROP|MOVE|COPY|ADD)\b',p.query,re.I):raise HTTPException(422,'Only local SELECT queries without external sources are supported')
    try:
        parsed=parseQuery(p.query)
        if parsed[1].name!='SelectQuery':raise ValueError('SELECT required')
        result=build_graph().query(p.query)
        return {'columns':[str(x) for x in result.vars],'rows':[[str(x) if x is not None else None for x in row] for _,row in zip(range(500),result)]}
    except Exception as e:raise HTTPException(422,'Invalid local SELECT: '+str(e)[:200])
@app.get('/api/insights')
def insights():
    MODEL.fit()
    with Session() as db:imports=[{**r.payload,'unrecognized_skill_count':len(r.payload.get('unrecognized_skills',[])),'unrecognized_skills':r.payload.get('unrecognized_skills',[])[:20]} for r in db.scalars(select(ImportLog))]
    path=ROOT/'results/evaluation.json'
    return {'model':MODEL.metadata,'weights':CFG,'triple_count':len(build_graph()),'imports':imports,'evaluation':json.loads(path.read_text()) if path.exists() else None,'warning':'Self-reported skills; matching indices are not probabilities of career success. DEMO DATA is not external validation.'}
@app.post('/api/datasets/inspect')
async def inspect(file:UploadFile=File(...)):
    content=await file.read(5_000_001)
    if len(content)>5_000_000:raise HTTPException(413,'CSV limit is 5 MB; use local import for larger files')
    try:
        df=pd.read_csv(BytesIO(content));return {'columns':list(df.columns),'rows':len(df),'missing':df.isna().sum().to_dict()}
    except Exception:raise HTTPException(422,'Could not read CSV')
@app.post('/api/datasets/import')
async def import_students(file:UploadFile=File(...),mapping:str=Form(...),source:str=Form(...)):
    content=await file.read(5_000_001)
    if len(content)>5_000_000:raise HTTPException(413,'CSV limit is 5 MB')
    try:return student_csv(content,json.loads(mapping),source[:300])
    except Exception as e:raise HTTPException(422,str(e)[:200])

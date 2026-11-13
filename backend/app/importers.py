"""Validated local imports. Student exports never retain direct identifiers."""
import csv, io, json, hashlib, re
from pathlib import Path
import pandas as pd
from sqlalchemy import select
from .store import Session, Catalog, ImportLog, ROOT
from .service import normalize, catalog, MODEL

def student_csv(content:bytes,mapping:dict,source:str):
    df=pd.read_csv(io.BytesIO(content)).fillna('')
    cols=[mapping.get(k) for k in ['skills','languages','soft_skills'] if mapping.get(k)]
    if not cols or any(c not in df.columns for c in cols):raise ValueError('Map at least one existing skills column')
    for key in ['rating','career','year','course']:
        if mapping.get(key) and mapping[key] not in df.columns:raise ValueError('Unknown mapped column: '+mapping[key])
    skills,_=catalog();out=[];seen=set();unknown=set()
    for _,row in df.iterrows():
        recognized=set()
        for col in cols:
            for raw in re.split(r'[,;|\n]+',str(row[col])):
                if not raw.strip():continue
                sid=normalize(raw,skills)
                if sid:recognized.add(sid)
                else:unknown.add(raw.strip())
        def value(k):return str(row[mapping[k]]) if mapping.get(k) else ''
        try:rating=float(value('rating')) if value('rating') else None
        except ValueError:rating=None
        rating=rating if rating is not None and 1<=rating<=5 else None
        obj={'skills':sorted(recognized),'self_reported_rating':rating,'career_preference':value('career'),'year':value('year'),'course':value('course')}
        key=json.dumps(obj,sort_keys=True)
        if recognized and key not in seen:out.append(obj);seen.add(key)
    digest=hashlib.sha256(content).hexdigest();path=ROOT/'data/processed'/f'students-{digest[:12]}.json'
    path.write_text(json.dumps(out,indent=2))
    log={'source':source,'sha256':digest,'input_rows':len(df),'accepted_rows':len(out),'removed_empty_or_duplicate':len(df)-len(out),'unrecognized_skills':sorted(unknown),'export':str(path.relative_to(ROOT)),'privacy':'Names/emails excluded; inspect free-text career/course before sharing','purpose':'Preference and self-report analysis only, not validated suitability','columns':list(df.columns)}
    with Session() as db:db.add(ImportLog(payload=log));db.commit()
    return log

def esco_csv(directory:Path,limit=40):
    """Official ESCO English CSV directory; subset selected by ISCO major group 25."""
    skills=pd.read_csv(directory/'skills_en.csv').fillna('');occ=pd.read_csv(directory/'occupations_en.csv').fillna('');rels=pd.read_csv(directory/'occupationSkillRelations_en.csv').fillna('')
    for df,cols in [(skills,['conceptUri','preferredLabel']),(occ,['conceptUri','preferredLabel','iscoGroup']),(rels,['occupationUri','skillUri','relationType'])]:
        if not set(cols)<=set(df.columns):raise ValueError('Missing ESCO columns: '+str(set(cols)-set(df.columns)))
    occ=occ[occ.iscoGroup.astype(str).str.startswith('25')].head(limit)
    rels=rels[rels.occupationUri.isin(occ.conceptUri)]
    if occ.empty or rels.empty:raise ValueError('No ISCO 25 occupation relationships found')
    if not set(rels.relationType)<={'essential','optional'}:raise ValueError('Unknown ESCO relationship type')
    skills=skills[skills.conceptUri.isin(rels.skillUri)]
    if not set(rels.skillUri)<=set(skills.conceptUri):raise ValueError('Dangling skill identifiers')
    source='ESCO official CSV, local import'
    with Session() as db:
        for _,s in skills.iterrows():db.merge(Catalog(id=s.conceptUri,kind='skill',payload={'id':s.conceptUri,'label':s.preferredLabel,'aliases':[x for x in str(s.get('altLabels','')).split('\n') if x],'source':source,'category':'technical','prerequisites':[],'effort_hours':20}))
        for _,o in occ.iterrows():db.merge(Catalog(id=o.conceptUri,kind='occupation',payload={'id':o.conceptUri,'label':o.preferredLabel,'description':o.get('description',''),'source':source,'requirements':[{'skill':r.skillUri,'type':r.relationType,'source':source} for _,r in rels[rels.occupationUri==o.conceptUri].iterrows()]}))
        checksums={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [directory/'skills_en.csv',directory/'occupations_en.csv',directory/'occupationSkillRelations_en.csv']}
        log={'source':source,'skills':len(skills),'occupations':len(occ),'relationships':len(rels),'file_sha256':checksums,'selection':'ISCO group prefix 25; first '+str(limit)};db.add(ImportLog(payload=log));db.commit()
    MODEL.signature=None;MODEL.fit();return log

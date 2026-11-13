import json, hashlib, time
from pathlib import Path
import numpy as np
import joblib
import networkx as nx
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, OWL, SKOS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select, delete
from .store import ROOT, Session, Student, Catalog, StudentSkill, Progress, ImportLog
CFG=json.loads((ROOT/'data/scoring.json').read_text())
SG=Namespace('https://skillgraph.local/vocab/')
DEMO=json.loads((ROOT/'data/demo.json').read_text())
def seed(reset=False):
    with Session() as db:
        for kind,key in [('skill','skills'),('occupation','occupations')]:
            for obj in DEMO[key]:
                if not db.get(Catalog,obj['id']): db.add(Catalog(id=obj['id'],kind=kind,payload=obj))
        snapshot_path=ROOT/'data/esco_snapshot.json'
        if snapshot_path.exists():
            snapshot=json.loads(snapshot_path.read_text())
            for kind,key in [('skill','skills'),('occupation','occupations')]:
                for obj in snapshot[key]:
                    if not db.get(Catalog,obj['id']):db.add(Catalog(id=obj['id'],kind=kind,payload=obj))
            if not any(x.payload.get('source')==snapshot['source'] for x in db.scalars(select(ImportLog))):
                db.add(ImportLog(payload={'source':snapshot['source'],'skills':len(snapshot['skills']),'occupations':len(snapshot['occupations']),'relationships':sum(len(o['requirements']) for o in snapshot['occupations']),'evidence':snapshot['evidence'],'note':snapshot['note']}))
        db.commit()
        if reset:
            for st in db.scalars(select(Student).where(Student.demo==True)).all(): db.delete(st)
            db.commit()
        if not db.scalar(select(Student).where(Student.demo==True)):
            for obj in DEMO['students']:
                st=Student(name=obj['name'],interests=obj['interests'],demo=True);db.add(st);db.flush()
                for sk,level in obj['skills'].items(): db.add(StudentSkill(student_id=st.id,skill_id=sk,proficiency=level))
        db.commit()
def catalog():
    with Session() as db:
        rows=db.scalars(select(Catalog)).all()
        return {r.id:r.payload for r in rows if r.kind=='skill'}, {r.id:r.payload for r in rows if r.kind=='occupation'}
def normalize(value,skills=None):
    skills=skills or catalog()[0]
    key=value.strip().casefold()
    for sid,s in skills.items():
        if key in [sid.casefold(),s['label'].casefold(),*[a.casefold() for a in s.get('aliases',[])]]:return sid
    return None
def profile(sid):
    with Session() as db:
        s=db.get(Student,sid)
        if not s:raise KeyError('Student not found')
        return {'id':s.id,'name':s.name,'course':s.course,'year':s.year,'interests':s.interests,'projects':s.projects,'demo':s.demo,'skills':{r.skill_id:r.proficiency for r in db.scalars(select(StudentSkill).where(StudentSkill.student_id==sid))}}
def token(s):return hashlib.sha256(s.encode()).hexdigest()[:24]
class Recommender:
    def __init__(self):self.signature=None
    def fit(self):
        skills,roles=catalog(); ordered=sorted(roles)
        signature=hashlib.sha256(json.dumps([skills,roles],sort_keys=True).encode()).hexdigest()
        if signature==self.signature:return
        saved=ROOT/'models/occupation_model.joblib'
        if saved.exists():
            try:
                obj=joblib.load(saved)
                if obj['metadata']['catalog_sha256']==signature:
                    self.ids=obj['ids'];self.vectorizer=obj['vectorizer'];self.svd=obj['svd'];self.matrix=obj['matrix'];self.metadata=obj['metadata'];self.mode=self.metadata['model'];self.signature=signature;return
            except (ValueError,TypeError,KeyError,ImportError,AttributeError):pass
        self.ids=ordered;self.vectorizer=TfidfVectorizer(tokenizer=str.split,token_pattern=None,lowercase=False)
        docs=[' '.join(token(r['skill']) for r in roles[oid]['requirements'] for _ in range(CFG['essential_weight'] if r['type']=='essential' else CFG['optional_weight'])) for oid in ordered]
        X=self.vectorizer.fit_transform(docs)
        n=min(8,X.shape[0]-1,X.shape[1]-1)
        self.svd=TruncatedSVD(n_components=n,random_state=CFG['random_state']) if n>=2 else None
        self.matrix=self.svd.fit_transform(X) if self.svd else X
        self.signature=signature;self.mode='TF-IDF + TruncatedSVD + cosine' if self.svd else 'TF-IDF + cosine (small-catalog fallback)'
        self.metadata={'model':self.mode,'occupation_count':len(ordered),'feature_count':X.shape[1],'components':n if self.svd else 0,'catalog_sha256':signature,'sources':sorted(set(r['source'] for r in roles.values())),'training_scope':'Unsupervised occupation-skill catalog only; no student outcomes or labels','random_state':42}
        (ROOT/'models').mkdir(exist_ok=True)
        joblib.dump({'vectorizer':self.vectorizer,'svd':self.svd,'matrix':self.matrix,'ids':self.ids,'metadata':self.metadata},ROOT/'models/occupation_model.joblib')
        (ROOT/'models/metadata.json').write_text(json.dumps(self.metadata,indent=2))
    def similarities(self,student_skills):
        self.fit()
        x=self.vectorizer.transform([' '.join(token(s) for s in student_skills)])
        if x.nnz==0:return {s:0.0 for s in self.ids}
        z=self.svd.transform(x) if self.svd else x
        return dict(zip(self.ids,np.clip(cosine_similarity(z,self.matrix)[0],0,1).tolist()))
MODEL=Recommender()
def build_graph():
    skills,roles=catalog();g=Graph();g.bind('sg',SG);g.bind('skos',SKOS);g.bind('owl',OWL)
    for kind in ['Student','Skill','Occupation','CareerInterest','Course','LearningResource','SkillCategory']:g.add((SG[kind],RDF.type,OWL.Class))
    def edge(a,p,b,source,kind):
        g.add((a,p,b));stmt=SG['statement/'+hashlib.sha256(f'{a}{p}{b}'.encode()).hexdigest()[:24]]
        for pred,obj in [(RDF.type,RDF.Statement),(RDF.subject,a),(RDF.predicate,p),(RDF.object,b),(SG.source,Literal(source)),(SG.origin,Literal(kind))]:g.add((stmt,pred,obj))
    for sid,s in skills.items():
        u=URIRef(sid) if sid.startswith('http') else SG['skill/'+sid]
        g.add((u,RDF.type,SG.Skill));g.add((u,RDF.type,SKOS.Concept));g.add((u,SKOS.prefLabel,Literal(s['label'])));g.add((u,SG.source,Literal(s['source'])))
        cat=SG['category/'+s.get('category','technical')];g.add((cat,RDF.type,SG.SkillCategory));edge(u,SG.inCategory,cat,'Project taxonomy','curated')
        for a in s.get('aliases',[]):g.add((u,SKOS.altLabel,Literal(a)))
        for p in s.get('prerequisites',[]):edge(u,SG.hasPrerequisite,skill_uri(p),'Project curated prerequisite','curated')
        res=SG['resource/'+token(sid)];g.add((res,RDF.type,SG.LearningResource));g.add((res,RDFS.label,Literal('Practice '+s['label'])));edge(res,SG.supportsSkill,u,'Project practice task','curated')
    for a,b in DEMO['related']:
        for x,y in [(a,b),(b,a)]:edge(skill_uri(x),SKOS.related,skill_uri(y),'Project curated related concept','curated')
    for oid,o in roles.items():
        u=occupation_uri(oid);g.add((u,RDF.type,SG.Occupation));g.add((u,RDFS.label,Literal(o['label'])))
        for r in o['requirements']:edge(u,SG.requiresEssential if r['type']=='essential' else SG.requiresOptional,skill_uri(r['skill']),r['source'],'imported' if not r['source'].startswith('DEMO') else 'curated')
    with Session() as db:
        for s in db.scalars(select(Student)):
            u=SG['student/'+str(s.id)];g.add((u,RDF.type,SG.Student));g.add((u,RDFS.label,Literal(s.name)))
            course=SG['course/'+token(s.course)];g.add((course,RDF.type,SG.Course));g.add((course,RDFS.label,Literal(s.course)));edge(u,SG.enrolledIn,course,'Student profile','self-reported')
            for r in db.scalars(select(StudentSkill).where(StudentSkill.student_id==s.id)):edge(u,SG.hasSkill,skill_uri(r.skill_id),'Student self-report','self-reported')
            for interest in s.interests:
                it=SG['interest/'+token(interest)];g.add((it,RDF.type,SG.CareerInterest));g.add((it,RDFS.label,Literal(interest)));edge(u,SG.interestedIn,it,'Student profile','self-reported')
    return g
def skill_uri(s):return URIRef(s) if s.startswith('http') else SG['skill/'+s]
def occupation_uri(s):return URIRef(s) if s.startswith('http') else SG['occupation/'+s]
def related_pairs():
    return set((str(a),str(b)) for a,b in build_graph().subject_objects(SKOS.related))
def rank(p,weights=None):
    weights=weights or CFG;skills,roles=catalog();known=p['skills']; sims=MODEL.similarities(known);rels=related_pairs();out=[]
    for oid,o in roles.items():
        req=o['requirements'];den=sum(CFG['essential_weight'] if r['type']=='essential' else CFG['optional_weight'] for r in req) or 1
        matched=[];missing=[];semantic_evidence=[];cov=sem=0
        for r in req:
            sid=r['skill'];w=CFG['essential_weight'] if r['type']=='essential' else CFG['optional_weight'];item={**r,'label':skills[sid]['label'],'proficiency':known.get(sid)}
            if sid in known:matched.append(item);cov+=w;sem+=w
            else:
                missing.append(item);near=[k for k in known if (str(skill_uri(k)),str(skill_uri(sid))) in rels]
                if near:sem+=w*CFG['related_credit'];semantic_evidence.append({'required':sid,'related_known':near,'credit':CFG['related_credit'],'source':'Project curated related concept'})
        c=cov/den;s=sem/den;m=sims[oid];score=100*(weights['coverage']*c+weights['semantic']*s+weights['ml']*m)
        out.append({**o,'score':round(score,4),'coverage':round(c*100,4),'components':{'coverage':c,'semantic':s,'ml':m},'contributions':{'coverage':100*weights['coverage']*c,'semantic':100*weights['semantic']*s,'ml':100*weights['ml']*m},'matching':matched,'missing_essential':[x for x in missing if x['type']=='essential'],'optional':[x for x in missing if x['type']=='optional'],'semantic_evidence':semantic_evidence,'explanation':'Engineering matching index: 50% weighted coverage + 20% graph match + 30% learned cosine similarity. Essential weight 2, optional 1. Related concepts receive 0.35 credit only in graph component. Self-reported proficiency is displayed, not a verified occupational threshold. Interests do not influence this skills-only score.'})
    return sorted(out,key=lambda x:(-x['score'],x['id']))
def gap(p,oid):
    found=next((r for r in rank(p) if r['id']==oid),None)
    if not found:raise KeyError('Occupation not found')
    return found
def roadmap(p,oid):
    r=gap(p,oid);skills,_=catalog();known=set(p['skills']);needed={x['skill']:x['type'] for x in r['missing_essential']+r['optional']};dag=nx.DiGraph()
    def add(s,trail=()):
        if s in trail:raise ValueError('Circular prerequisite dependency')
        if s in known:return
        dag.add_node(s)
        for pre in skills[s].get('prerequisites',[]):
            if pre not in skills:raise ValueError('Unknown prerequisite')
            if pre not in known:add(pre,trail+(s,));dag.add_edge(pre,s)
    for s in list(needed):add(s)
    order=list(nx.lexicographical_topological_sort(dag,key=lambda s:(0 if needed.get(s)=='essential' else 1,skills[s]['label'])))
    with Session() as db:done={x.skill_id:x.completed for x in db.scalars(select(Progress).where(Progress.student_id==p['id'],Progress.occupation_id==oid))}
    return [{'skill':s,'label':skills[s]['label'],'stage':i+1,'importance':needed.get(s,'prerequisite'),'prerequisites':skills[s].get('prerequisites',[]),'objective':'Explain and apply '+skills[s]['label']+' in a reproducible exercise.','practice':'Build a small '+skills[s]['label']+' example, document inputs and results, and test one failure case.','estimated_hours':skills[s].get('effort_hours',20),'estimate_source':'Project planning estimate, not dataset evidence','completed':done.get(s,False)} for i,s in enumerate(order)]
QUERIES={
 'requirements':'PREFIX sg: <https://skillgraph.local/vocab/> SELECT ?occupation ?skill WHERE { ?occupation sg:requiresEssential ?skill } LIMIT 100',
 'shared':'PREFIX sg: <https://skillgraph.local/vocab/> SELECT ?student ?skill ?occupation WHERE { ?student sg:hasSkill ?skill . ?occupation sg:requiresEssential ?skill } LIMIT 100',
 'prerequisites':'PREFIX sg: <https://skillgraph.local/vocab/> SELECT ?skill ?prerequisite WHERE { ?skill sg:hasPrerequisite ?prerequisite } LIMIT 100'}
def subgraph(p,oid):
    r=gap(p,oid);skills,_=catalog();nodes=[{'data':{'id':'student','label':p['name'],'kind':'student','source':'Self-reported profile'}},{'data':{'id':'occupation','label':r['label'],'kind':'occupation','source':r['source']}}];edges=[];seen=set()
    for req in r['requirements']:
        s=req['skill'];seen.add(s);nodes.append({'data':{'id':s,'label':skills[s]['label'],'kind':'matching' if s in p['skills'] else 'missing','source':skills[s]['source']}});edges.append({'data':{'id':'req'+s,'source':'occupation','target':s,'label':req['type'],'provenance':req['source']}})
        if s in p['skills']:edges.append({'data':{'id':'has'+s,'source':'student','target':s,'label':'has skill','provenance':'Self-report'}})
    for e in r['semantic_evidence']:
        for k in e['related_known']:
            if k not in seen:nodes.append({'data':{'id':k,'label':skills[k]['label'],'kind':'related','source':skills[k]['source']}});seen.add(k);edges.append({'data':{'id':'has'+k,'source':'student','target':k,'label':'has skill','provenance':'Self-report'}})
            edges.append({'data':{'id':'rel'+k+e['required'],'source':k,'target':e['required'],'label':'related (0.35)','provenance':e['source']}})
    return nodes+edges

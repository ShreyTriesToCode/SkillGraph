import os,sys,tempfile,json
from pathlib import Path
os.environ['SKILLGRAPH_DB']='sqlite:///'+str(Path(tempfile.mkdtemp())/'test.db')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.service import normalize,build_graph,QUERIES,MODEL,rank,roadmap,catalog,SG
from app.store import Session,Catalog
from app.importers import student_csv,esco_csv
@pytest.fixture(scope='module')
def client():
    with TestClient(app) as c:yield c

def test_health_and_seed(client):
    assert client.get('/api/health').json()['status']=='ok'
    assert len(client.get('/api/students').json())==3

def test_aliases(client):
    assert normalize(' PYTHON3 ')=='python'
    assert normalize('basic cloud computing')=='cloud-computing'
    assert normalize('unknown') is None

def test_recommendation_workflow(client):
    ss=client.post('/api/demo/reset').json();s=ss[0];sid=s['id']
    ranks=client.get(f'/api/students/{sid}/recommendations').json()['recommendations'];old=next(r for r in ranks if r['id']=='data-engineer')
    assert 'etl' in [r['skill'] for r in old['missing_essential']]
    g=client.get('/api/graph',params={'sid':sid,'occupation':'data-engineer'}).json()
    assert any(x['data'].get('id')=='etl' and x['data']['kind']=='missing' for x in g['elements'])
    body={k:s[k] for k in ['name','course','year','skills','interests','projects']};body['skills']['etl']=3
    assert client.put(f'/api/students/{sid}',json=body).status_code==200
    new=client.get(f'/api/students/{sid}/gap',params={'occupation':'data-engineer'}).json()
    assert new['score']>old['score'];assert new['coverage']>old['coverage']
    assert 'etl' not in [r['skill'] for r in new['missing_essential']]
    steps=client.get(f'/api/students/{sid}/roadmap',params={'occupation':'data-engineer'}).json();ids=[r['skill'] for r in steps]
    assert ids.index('database-design')<ids.index('data-warehousing')
    params={'occupation':'data-engineer','skill':ids[0]}
    assert client.put(f'/api/students/{sid}/progress',params=params,json={'completed':True}).status_code==200
    again=client.get(f'/api/students/{sid}/roadmap',params={'occupation':'data-engineer'}).json();assert again[0]['completed']
    client.put(f'/api/students/{sid}/progress',params=params,json={'completed':True,'acquired':True,'proficiency':4})
    assert client.get(f'/api/students/{sid}').json()['skills'][ids[0]]==4
    assert ids[0] not in [r['skill'] for r in client.get(f'/api/students/{sid}/roadmap',params={'occupation':'data-engineer'}).json()]

def test_profile_validation(client):
    body={'name':'Anon','skills':{'py':4},'year':2}
    r=client.post('/api/students',json=body);assert r.status_code==201
    assert r.json()['skills']=={'python':4}
    assert client.post('/api/students',json={'name':'X','skills':{'Unknown':3}}).status_code==422
    assert client.post('/api/students',json={'name':'X','skills':{'python':9}}).status_code==422
    assert client.get('/api/students/999999').status_code==404
    assert client.get('/api/students/1/gap',params={'occupation':'unknown'}).status_code==404

def test_graph_sparql_and_block_network(client):
    assert len(build_graph())>400
    for q in QUERIES.values():
        r=client.post('/api/graph/query',json={'query':q});assert r.status_code==200;assert len(r.json()['rows'])>0
    assert client.post('/api/graph/query',json={'query':'SELECT * WHERE { SERVICE <http://example.com> {?s ?p ?o}}'}).status_code==422
    assert client.post('/api/graph/query',json={'query':'DELETE WHERE {?s ?p ?o}'}).status_code==422
    assert 'Statement' in client.get('/api/graph/triples').text

def test_model_reproducible_and_load(client,monkeypatch):
    import joblib,numpy as np
    from app.service import ROOT
    p={'id':1,'skills':{'python':3,'sql':3}}
    a=rank(p);MODEL.signature=None
    # Exercise a fresh deterministic fit, independently of loading the saved artifact.
    with monkeypatch.context() as patch:
        def reject_cached_model(*args,**kwargs):raise ValueError('Force fresh fit for reproducibility check')
        patch.setattr(joblib,'load',reject_cached_model)
        b=rank(p)
    assert [(r['id'],r['score']) for r in a]==[(r['id'],r['score']) for r in b]
    assert all(0<=r['score']<=100 for r in a)
    loaded=joblib.load(ROOT/'models/occupation_model.joblib');assert loaded['metadata']['random_state']==42
    assert all(r['score']==0 for r in rank({'id':1,'skills':{}}))

def test_import_privacy_and_missing(client):
    content=b'Name,email_id,Technical Skills,Rating,Career\nJane,jane@example.com,"Python; SQL; py",3,Data\nJane,jane@example.com,"Python; SQL; py",3,Data\nAnon,x@example.com,Unknown,9,Web\n'
    log=student_csv(content,{'skills':'Technical Skills','rating':'Rating','career':'Career'},'TEST CSV')
    assert log['accepted_rows']==1;assert log['removed_empty_or_duplicate']==2
    from app.service import ROOT
    data=(ROOT/log['export']).read_text();assert 'Jane' not in data and '@' not in data;assert 'Unknown' in log['unrecognized_skills']
    with pytest.raises(ValueError):student_csv(content,{'skills':'not a column'},'TEST')

def test_roadmap_cycle_guard(client):
    with Session() as db:
        obj=db.get(Catalog,'python');old=dict(obj.payload);obj.payload={**old,'prerequisites':['etl']};db.commit()
    try:
        with pytest.raises(ValueError,match='Circular'):roadmap({'id':1,'skills':{}},'data-engineer')
    finally:
        with Session() as db:db.get(Catalog,'python').payload=old;db.commit()

def test_upload_schema(client):
    r=client.post('/api/datasets/inspect',files={'file':('test.csv',b'Skill,Career\nPython,Data\n','text/csv')});assert r.json()['columns']==['Skill','Career']
    r=client.post('/api/datasets/import',files={'file':('test.csv',b'Skill,Career\nPython,Data\n','text/csv')},data={'mapping':json.dumps({'skills':'Skill','career':'Career'}),'source':'TEST upload'});assert r.status_code==200

def test_esco_csv_import_preserves_uris_and_rejects_dangling(client,tmp_path):
    import pandas as pd
    uri='http://data.europa.eu/esco/skill/test-concept';occ='http://data.europa.eu/esco/occupation/test-occupation'
    pd.DataFrame([{'conceptUri':uri,'preferredLabel':'Test official skill'}]).to_csv(tmp_path/'skills_en.csv',index=False)
    pd.DataFrame([{'conceptUri':occ,'preferredLabel':'Test official role','iscoGroup':'2511'}]).to_csv(tmp_path/'occupations_en.csv',index=False)
    pd.DataFrame([{'occupationUri':occ,'skillUri':uri,'relationType':'essential'}]).to_csv(tmp_path/'occupationSkillRelations_en.csv',index=False)
    log=esco_csv(tmp_path);assert log['relationships']==1
    sk,oc=catalog();assert sk[uri]['id']==uri;assert oc[occ]['requirements'][0]['type']=='essential'
    pd.DataFrame([{'occupationUri':occ,'skillUri':'http://example.invalid/missing','relationType':'essential'}]).to_csv(tmp_path/'occupationSkillRelations_en.csv',index=False)
    with pytest.raises(ValueError,match='Dangling'):esco_csv(tmp_path)

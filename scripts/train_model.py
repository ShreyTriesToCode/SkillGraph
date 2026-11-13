import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.service import seed, MODEL, build_graph, ROOT
seed();MODEL.fit();build_graph().serialize(ROOT/'data/processed/knowledge_graph.ttl',format='turtle');print(MODEL.metadata)

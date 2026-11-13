"""Held-out-skill retrieval proxy. No career suitability ground truth is claimed."""
import sys,json,time,statistics,csv
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from app.service import seed,MODEL,catalog,rank,ROOT,CFG
seed();MODEL.fit();skills,roles=catalog();rows=[]
# Query = all but one essential skill; relevance = occupations requiring the held-out skill.
# Occupational model deliberately sees the catalog. This is transductive catalog retrieval,
# not a held-out occupation test or career-outcome prediction experiment.
for oid,o in sorted(roles.items()):
    ess=sorted(r['skill'] for r in o['requirements'] if r['type']=='essential')
    for hidden in ess:
        known={s:3 for s in ess if s!=hidden};p={'id':-1,'skills':known}
        relevant={k for k,v in roles.items() if any(r['skill']==hidden and r['type']=='essential' for r in v['requirements'])}
        start=time.perf_counter(); ranked=rank(p);elapsed=(time.perf_counter()-start)*1000
        methods={'exact_keyword':lambda r:len(set(known)&{q['skill'] for q in r['requirements']}), 'weighted_overlap':lambda r:r['components']['coverage'],'ml_similarity':lambda r:r['components']['ml'],'hybrid':lambda r:r['score'],'hybrid_coverage_heavy':lambda r:.7*r['components']['coverage']+.1*r['components']['semantic']+.2*r['components']['ml'],'hybrid_ml_heavy':lambda r:.3*r['components']['coverage']+.2*r['components']['semantic']+.5*r['components']['ml']}
        for method,fn in methods.items():
            begin=time.perf_counter();top=sorted(ranked,key=lambda r:(-fn(r),r['id']))[:3];latency=elapsed+(time.perf_counter()-begin)*1000
            hits=len({r['id'] for r in top}&relevant)
            rows.append({'query_occupation':oid,'hidden_skill':hidden,'method':method,'recall_at_3':hits/len(relevant),'latency_ms':latency,'relevant_count':len(relevant),'top3':'|'.join(r['id'] for r in top)})
summary=[{'method':m,'recall_at_3':statistics.mean(r['recall_at_3'] for r in rows if r['method']==m),'median_latency_ms':statistics.median(r['latency_ms'] for r in rows if r['method']==m)} for m in methods]
result={'description':'Leave-one-essential-skill-out retrieval proxy over the current mixed-source occupational catalog. Relevance means sharing the hidden essential skill. This is a diagnostic, not independent career suitability evaluation. Latency includes a shared full hybrid pipeline for every method and is not a fair method speed comparison.','query_count':len(rows)//len(methods),'source':sorted(set(o['source'] for o in roles.values())),'random_state':42,'summary':summary,'limitations':['Correlated queries from a small curated catalog','Occupation vectors use the complete catalog; transductive skill retrieval only','No independently judged student-career labels','No statistical claim of hybrid superiority'],'weights':CFG}
(ROOT/'results/evaluation.json').write_text(json.dumps(result,indent=2))
with (ROOT/'results/evaluation.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
fig,ax=plt.subplots(figsize=(9,4.2));ax.barh([s['method'].replace('_',' ') for s in summary],[s['recall_at_3'] for s in summary],color=['#acb8d5','#8f9fc9','#7586c4','#5164d5','#6274d1','#7888d8']);ax.set_xlim(0,1);ax.set_xlabel('Mean held-out skill recall@3 (catalog proxy)');ax.set_title('Reproducible diagnostic — not career accuracy',loc='left',fontsize=13,pad=15);ax.spines[['top','right']].set_visible(False)
for i,s in enumerate(summary):ax.text(s['recall_at_3']+.01,i,f"{s['recall_at_3']:.3f}",va='center',fontsize=10)
fig.tight_layout();fig.savefig(ROOT/'results/evaluation.png',dpi=200);print(json.dumps(result,indent=2))

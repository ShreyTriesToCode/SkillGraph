"""Check application files after dependency installation and model generation."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--application-only',action='store_true',help='Validate application files')
p.parse_args()
required=['frontend/src/main.tsx','frontend/dist/index.html','backend/app/main.py','data/demo.json','data/esco_snapshot.json','models/occupation_model.joblib','scripts/run_demo.sh']
missing=[f for f in required if not (ROOT/f).is_file() or (ROOT/f).stat().st_size==0]
report={'missing':missing,'checked_files':len(required),'status':'pass' if not missing else 'incomplete'}
(ROOT/'results').mkdir(exist_ok=True)
(ROOT/'results/deliverable-validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
sys.exit(bool(missing))

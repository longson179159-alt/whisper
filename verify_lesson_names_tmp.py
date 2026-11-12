from pathlib import Path 
import json, re 
root=Path(r'C:\Users\PC\Desktop\kaggle\whisper\en\a2\LEARNE~1\lessons') 
failures=[] 
for p in root.iterdir(): 
    if not p.is_dir(): continue 
    d=json.loads((p/'description.json').read_text(encoding='utf-8-sig')) 
    slug=re.sub(r'[A-Za-z0-9]+','_',d['lesson_name']).strip('_') 
    expected=str(d['lesson_number'])+'.'+slug 
    if p.name != expected: failures.append((p.name,expected)) 
print('FOLDER_COUNT',sum(p.is_dir() for p in root.iterdir())) 
print('MISMATCHES',failures)

from pathlib import Path 
import json, re 
root = Path(r'C:\Users\PC\Desktop\kaggle\whisper\en\a2\LEARNE~1\lessons') 
rows = [] 
for folder in root.iterdir(): 
    if not folder.is_dir(): continue 
    data = json.loads((folder / 'description.json').read_text(encoding='utf-8-sig')) 
    number = data.get('lesson_number') 
    name = data.get('lesson_name') or folder.name 
    slug = re.sub(r'[A-Za-z0-9]+', '_', name).strip('_') 
    rows.append((folder, f'{int(number)}.{slug}' if number is not None else None, number)) 
targets = [new for _,new,_ in rows if new] 
if len(targets) != len(set(targets)): raise SystemExit('Collision detected') 
if any(new is None for _,new,_ in rows): raise SystemExit('Missing lesson number') 
for old,new,_ in rows: 
    if old.name != new and (root/new).exists(): raise SystemExit('Target exists: '+new) 
print('PLAN') 
for old,new,number in sorted(rows,key=lambda r:r[2]): print(old.name,'=>',new) 
for old,new,_ in rows: 
    if old.name != new: old.rename(root/new) 
print('RENAMED', sum(old.name != new for old,new,_ in rows))

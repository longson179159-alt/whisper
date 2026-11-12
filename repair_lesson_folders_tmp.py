from pathlib import Path 
import json, re 
root=Path(r'C:\Users\PC\Desktop\kaggle\whisper\en\a2\LEARNE~1\lessons') 
rows=[] 
for folder in root.iterdir(): 
    if folder.is_dir(): 
        data=json.loads((folder/'description.json').read_text(encoding='utf-8-sig')) 
        normalized=re.sub(r'[A-Za-z0-9]+','_',data['lesson_name']).strip('_') 
        rows.append((folder,str(data['lesson_number'])+'.'+normalized)) 
destinations=[name for _,name in rows] 
if len(destinations)!=len(set(destinations)): raise SystemExit('Name collision; stopped') 
print('REPAIR PLAN') 
for old,new in sorted(rows,key=lambda x:int(x[1].split('.')[0])): print(old.name,'to',new) 
for old,new in rows: 
    if old.name!=new: old.rename(root/('TEMP_REPAIR_'+new)) 
for _,new in rows: 
    temp=root/('TEMP_REPAIR_'+new) 
    if temp.exists(): temp.rename(root/new) 
print('RENAMED',len(rows))

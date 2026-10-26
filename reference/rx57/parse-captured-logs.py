from pathlib import Path
import json,runpy
root=Path(__file__).resolve().parent
parse=runpy.run_path(str(root/'parse-driver-log.py'))['parse']
out=root/'parsed-02';out.mkdir(exist_ok=True)
for path in sorted((root/'driver-logs-02').glob('*.log')):
    result,wire=parse(path)
    (out/(path.name+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    (out/(path.name+'.read.raw')).write_bytes(wire)
    print(json.dumps({k:v for k,v in result.items() if k!='records'}))

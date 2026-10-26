from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel367'
assert json.loads((HERE/'current-health-validation.json').read_text())['healthy']
for name in ['camera-check.py','camera-check-body.py','final-state.py']:
 s=(OLD/name).read_text().replace('k367','k369').replace('stage=367','stage=369').replace("'stage':367","'stage':369")
 if name=='camera-check.py':s=s.replace("HERE/'services-ready-validation.json'","HERE/'current-health-validation.json'").replace(")['ready']",")['healthy']").replace("HERE/'postboot-validation.json'","HERE/'recovery-cleanup-validation.json'")
 if name=='camera-check-body.py':s=s.replace('/var/lib/samurai/k369-work/boot-id-private.txt','/var/lib/samurai/k369-recovered/boot-id-private.txt')
 if name=='final-state.py':s=s.replace("ssh='strict_original_key_usb'","ssh='strict_original_key_wifi'")
 compile(s,name,'exec');(HERE/name).write_text(s)
p=HERE/'collect-retained-firmware.py';s=p.read_text().replace('stage=368','stage=369');p.write_text(s)
p=HERE/'retained-firmware-validation.json';d=json.loads(p.read_text());d['stage']=369;p.write_text(json.dumps(d,indent=2)+'\n')
print('Prepared baseline recovery checks on adopted369 boot; no additional reboot needed because SSC/desktop are healthy.')

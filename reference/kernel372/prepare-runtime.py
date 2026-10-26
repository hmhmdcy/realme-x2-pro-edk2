from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel371'
for name in ['observer','lifecycle','decoder','intree-build']:assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
for name in ['snapshot-collector.py','check-worker.py']:
 (HERE/name).write_text((OLD/name).read_text().replace('stage=371','stage=372'))
s=(OLD/'boot-worker.py').read_text()
anchor="run(['insmod',str(ROOT/'test.ko'),'hold_start_failure=1'])";assert s.count(anchor)==1
s=s.replace(anchor,"run(['insmod',str(ROOT/'test.ko'),'hold_start_failure=1','snapshot_offsets='+','.join(str(w['offset']) for w in meta['snapshot_profile']['windows']),'snapshot_words='+','.join(str(w['words']) for w in meta['snapshot_profile']['windows'])])")
compile(s,'boot-worker.py','exec');(HERE/'boot-worker.py').write_text(s)
s=(OLD/'launch-boot.py').read_text().replace('k371-boot-','k372-boot-').replace("['collector','worker','lifecycle','intree-build']","['observer','decoder','worker','lifecycle','intree-build']").replace("kernel369/recovered-boot-adoption-private.json","kernel371/recovered-boot-adoption-private.json")
s=s.replace("boot_guard=json.loads((P.parent/'kernel369/recovered-boot-adoption-private.json')", "boot_guard=json.loads((P.parent/'kernel371/recovered-boot-adoption-private.json')")
anchor=" payload_sha256={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()},firmware_sha256=hashlib.sha256(fw).hexdigest(),";assert s.count(anchor)==1
s=s.replace(anchor," snapshot_profile=json.loads((HERE/'firmware-context-validation.json').read_text()),\n"+anchor)
s=s.replace('Prepared371','Prepared372');compile(s,'launch-boot.py','exec');(HERE/'launch-boot.py').write_text(s)
s=(OLD/'poll-boot.py').read_text().replace('k371-boot-','k372-boot-').replace('stage=371','stage=372');(HERE/'poll-boot.py').write_text(s)
s=(OLD/'collect-recovery.py').read_text().replace('k371-boot-','k372-boot-').replace('k369-recovered','k371-recovered').replace('stage=371','stage=372')
# Keep the old inventory-template token replacement pointing at this run.
s=s.replace(".replace('k356-boot-r5','k371-boot-r1')", ".replace('k356-boot-r5','k372-boot-r1')")
(HERE/'collect-recovery.py').write_text(s)
print('Prepared372: observer ranges supplied explicitly from verified OEM instruction profile; no launch yet.')

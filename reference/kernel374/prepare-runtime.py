from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel373'
for name in ['snapshot-collector.py','check-worker.py','decode-ramoops.py','decode-current.py','poll-boot.py','collect-recovery.py','preflight.py']:
 s=(OLD/name).read_text().replace('stage=373','stage=374').replace('k373-boot-','k374-boot-').replace('current372_guard_verified','current373_guard_verified')
 if name=='collect-recovery.py':s=s.replace('k372-recovered','k373-recovered')
 (HERE/name).write_text(s)
(HERE/'firmware-context-validation.json').write_bytes((OLD/'firmware-context-validation.json').read_bytes())
s=(OLD/'boot-worker.py').read_text()
anchor=" deadline=time.monotonic()+20\n while True:\n  result=read_result();save('boot-test',device_result=result)";assert s.count(anchor)==1
block=''' ready_result=read_result()
 assert ready_result.get('terminal') and ready_result.get('phase')=='ready' and not ready_result.get('error') and not ready_result.get('cpu_release_attempted') and not ready_result.get('irq_enabled') and releasable(ready_result),'Probe did not return a resource-only ready state'
 assert Path('/sys/module',test,'parameters/bound_seen').read_text().strip()=='Y','Platform binding notification not complete'
 assert collector.poll() is None,'Collector ended before explicit firmware run'
 save('binding-ready',device_result=ready_result,binding_returned_before_cpu_release=True)
 save('explicit-post-bind-run')
 Path('/sys/bus/platform/devices/ac10000.samurai-icp356-boot/run').write_text('1')
'''
s=s.replace(anchor,block+anchor);compile(s,'boot-worker.py','exec');(HERE/'boot-worker.py').write_text(s)
s=(OLD/'launch-boot.py').read_text().replace('k373-boot-','k374-boot-').replace('Prepared373','Prepared374').replace("['order','worker','lifecycle','intree-build']","['owner','dispatch','worker','intree-build']").replace("P.parent/'kernel372/recovered-boot-adoption-private.json'","P.parent/'kernel373/recovered-boot-adoption-private.json'")
(HERE/'launch-boot.py').write_text(s)
print('Prepared explicit post-binding execution; no CPU start occurs during module probe.')

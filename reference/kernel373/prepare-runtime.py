from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel372'
for name in ['boot-worker.py','snapshot-collector.py','check-worker.py','decode-ramoops.py','decode-current.py','preflight.py','poll-boot.py','collect-recovery.py']:
 s=(OLD/name).read_text().replace('stage=372','stage=373').replace('k372-boot-','k373-boot-').replace('current371_guard_verified','current372_guard_verified')
 if name=='collect-recovery.py':s=s.replace('k371-recovered','k372-recovered')
 (HERE/name).write_text(s)
(HERE/'firmware-context-validation.json').write_bytes((OLD/'firmware-context-validation.json').read_bytes())
s=(OLD/'launch-boot.py').read_text().replace('k372-boot-','k373-boot-').replace('Prepared372','Prepared373').replace("['observer','decoder','worker','lifecycle','intree-build']","['order','worker','lifecycle','intree-build']").replace("kernel371/recovered-boot-adoption-private.json","kernel372/recovered-boot-adoption-private.json").replace("P.parent/'kernel371/recovered-boot-adoption-private.json'","P.parent/'kernel372/recovered-boot-adoption-private.json'")
(HERE/'launch-boot.py').write_text(s)
print('Prepared373 guarded functional reset/wake/HFI-order experiment, using retained372 observer and current372 guard.')

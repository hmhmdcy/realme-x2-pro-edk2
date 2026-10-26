from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel377';P=host.PRIVATE
for name in ['boot-worker.py','snapshot-collector.py','check-worker.py','check-dispatch.py','poll-boot.py','preflight.py','launch-boot.py','current-health.py','check-session.py','session-regression.c','check-owner.py','owner-regression.c','check-encoder.py']:
 s=(OLD/name).read_text().replace('stage=377','stage=378').replace('k377-boot-','k378-boot-').replace('Prepared377','Prepared378')
 if name=='launch-boot.py':s=s.replace("P.parent/'kernel374/recovered-boot-adoption-private.json'","P.parent/'kernel377/recovered-boot-adoption-private.json'")
 if name=='preflight.py':s=s.replace('current374_guard_verified','current377_guard_verified')
 (HERE/name).write_text(s)
for name in ['firmware-context-validation.json','hal-io-validation.json','firmware-io-validation.json']:(HERE/name).write_bytes((OLD/name).read_bytes())
(P/'hal-io-cases-private.json').write_bytes((P.parent/'kernel377/hal-io-cases-private.json').read_bytes())
s=(OLD/'apply-source.py').read_text().replace('samurai-a5-ipe-io377','samurai-a5-command-window378').replace('media: camss: configure A5 IPE IO with owned firmware buffer mappings','media: camss: keep command memory outside firmware debug queue mappings')
s=s.replace("P.parent/'kernel376/live-overlay-state-private.json'","P.parent/'kernel377/live-overlay-state-private.json'").replace("HERE.parent/'kernel376/build-intree.py'","HERE.parent/'kernel377/build-intree.py'").replace(".replace('stage=376','stage=377')",".replace('stage=377','stage=378')")
(HERE/'apply-source.py').write_text(s)
print('Prepared378 targeted correction and fresh guarded experiment; prior377 failure remains unchanged.')

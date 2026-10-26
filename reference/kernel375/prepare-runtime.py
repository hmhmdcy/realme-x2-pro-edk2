from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel374';P=host.PRIVATE
for name in ['boot-worker.py','snapshot-collector.py','check-worker.py','check-dispatch.py','decode-ramoops.py','decode-current.py','poll-boot.py','collect-recovery.py','preflight.py','launch-boot.py','current-health.py','adopt-recovered-boot.py']:
 s=(OLD/name).read_text().replace('stage=374','stage=375').replace('k374-boot-','k375-boot-').replace('Prepared374','Prepared375').replace('current373_guard_verified','current374_guard_verified')
 if name in ['collect-recovery.py','adopt-recovered-boot.py']:s=s.replace('k373-recovered','k374-recovered')
 if name=='adopt-recovered-boot.py':s=s.replace("directory=Path('/var/lib/samurai/k374-recovered')", "directory=Path('/var/lib/samurai/k375-recovered')")
 if name=='launch-boot.py':
  s=s.replace("['owner','dispatch','worker','intree-build']","['stop','dispatch','worker','intree-build']").replace("P.parent/'kernel373/recovered-boot-adoption-private.json'","P.parent/'kernel374/recovered-boot-adoption-private.json'")
 compile(s,name,'exec');(HERE/name).write_text(s)
(HERE/'firmware-context-validation.json').write_bytes((OLD/'firmware-context-validation.json').read_bytes())
s=(OLD/'apply-source.py').read_text().replace("HERE/'owner-validation.json'","HERE/'stop-validation.json'").replace('samurai-a5-post-bind374','samurai-a5-cooperative-stop375').replace('media: camss: run temporary A5 lifecycle only after platform binding','media: camss: avoid global ICP reset during cooperative A5 shutdown').replace("P.parent/'kernel373/live-overlay-state-private.json'","P.parent/'kernel374/live-overlay-state-private.json'").replace("HERE.parent/'kernel373/build-intree.py'","HERE.parent/'kernel374/build-intree.py'").replace(".replace('stage=373','stage=374')",".replace('stage=374','stage=375')")
(HERE/'apply-source.py').write_text(s)
print('Prepared targeted375 lifecycle experiment with recovered374 guard; unchanged post-bind owner/worker.')

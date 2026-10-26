from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel375'
for name in ['boot-worker.py','snapshot-collector.py','check-worker.py','check-dispatch.py','poll-boot.py','preflight.py','launch-boot.py','current-health.py']:
 s=(OLD/name).read_text().replace('stage=375','stage=376').replace('k375-boot-','k376-boot-').replace('Prepared375','Prepared376')
 if name=='launch-boot.py':s=s.replace("['stop','dispatch','worker','intree-build']","['firmware-session','session','owner','dispatch','worker','intree-build']")
 if name=='boot-worker.py':
  anchor=" observation['firmware_handshake_passed']=handshake"
  assert s.count(anchor)==1
  s=s.replace(anchor," sessions=bool(result.get('session_creates')==2 and result.get('session_destroys')==2 and result.get('session_peak')==2 and not result.get('image_sessions') and not result.get('session_uncertain') and result.get('image_frames')==0)\n observation['ipe_session_lifecycle_passed']=sessions\n"+anchor)
  s=s.replace(" observation['passed']=handshake", " observation['passed']=handshake and sessions")
 if name=='poll-boot.py':s=s.replace("'binding_returned_before_cpu_release',", "'ipe_session_lifecycle_passed','binding_returned_before_cpu_release',")
 if name=='check-worker.py':
  s=s.replace("if case=='ready':initial.update(error=0,", "if case=='ready':initial.update(session_creates=2,session_destroys=2,session_peak=2,image_sessions=0,session_uncertain=False,image_frames=0,error=0,")
  s=s.replace("if case=='ready':assert observation['firmware_handshake_passed']", "if case=='ready':assert observation['firmware_handshake_passed'] and observation['ipe_session_lifecycle_passed'] and observation['passed']")
 compile(s,name,'exec');(HERE/name).write_text(s)
(HERE/'firmware-context-validation.json').write_bytes((OLD/'firmware-context-validation.json').read_bytes())
s=(OLD/'apply-source.py').read_text().replace("HERE/'stop-validation.json'","HERE/'session-validation.json'").replace('samurai-a5-cooperative-stop375','samurai-a5-ipe-session376').replace('media: camss: avoid global ICP reset during cooperative A5 shutdown','media: camss: add A5 IPE RT and non-RT session lifecycle')
s=s.replace("P.parent/'kernel374/live-overlay-state-private.json'","P.parent/'kernel375/live-overlay-state-private.json'").replace("HERE.parent/'kernel374/build-intree.py'","HERE.parent/'kernel375/build-intree.py'").replace(".replace('stage=374','stage=375')",".replace('stage=375','stage=376')")
(HERE/'apply-source.py').write_text(s)
print('Prepared376 explicit post-bind IPE session experiment; guarded current374 boot unchanged.')

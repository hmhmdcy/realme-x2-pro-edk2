from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel376'
for name in ['boot-worker.py','snapshot-collector.py','check-worker.py','check-dispatch.py','poll-boot.py','preflight.py','launch-boot.py']:
 s=(OLD/name).read_text().replace('stage=376','stage=377').replace('k376-boot-','k377-boot-').replace('Prepared376','Prepared377')
 if name=='launch-boot.py':s=s.replace("['firmware-session','session','owner','dispatch','worker','intree-build']", "['hal-io','firmware-io','encoder','session','owner','dispatch','worker','intree-build']")
 if name=='boot-worker.py':
  anchor=" observation['passed']=handshake and sessions";assert s.count(anchor)==1
  s=s.replace(anchor," io=bool(result.get('io_configs')==2 and result.get('config_maps')==2 and result.get('config_unmaps')==2 and not result.get('config_fw_mapped') and len(result.get('scratch_bytes',[]))==2)\n observation['ipe_io_config_passed']=io\n observation['passed']=handshake and sessions and io")
 if name=='poll-boot.py':s=s.replace("'ipe_session_lifecycle_passed',", "'ipe_io_config_passed','ipe_session_lifecycle_passed',")
 if name=='check-worker.py':
  s=s.replace('session_creates=2,','io_configs=2,config_maps=2,config_unmaps=2,config_fw_mapped=False,scratch_bytes=[65536,65536],session_creates=2,')
  s=s.replace("and observation['ipe_session_lifecycle_passed'] and observation['passed']", "and observation['ipe_session_lifecycle_passed'] and observation['ipe_io_config_passed'] and observation['passed']")
 compile(s,name,'exec');(HERE/name).write_text(s)
(HERE/'firmware-context-validation.json').write_bytes((OLD/'firmware-context-validation.json').read_bytes())
s=(OLD/'apply-source.py').read_text().replace('samurai-a5-ipe-session376','samurai-a5-ipe-io377').replace('media: camss: add A5 IPE RT and non-RT session lifecycle','media: camss: configure A5 IPE IO with owned firmware buffer mappings')
s=s.replace("P.parent/'kernel375/live-overlay-state-private.json'","P.parent/'kernel376/live-overlay-state-private.json'").replace("HERE.parent/'kernel375/build-intree.py'","HERE.parent/'kernel376/build-intree.py'").replace(".replace('stage=375','stage=376')",".replace('stage=376','stage=377')")
(HERE/'apply-source.py').write_text(s)
print('Prepared377 guarded MAP/CONFIG/UNMAP experiment without image DMA/frame submission.')

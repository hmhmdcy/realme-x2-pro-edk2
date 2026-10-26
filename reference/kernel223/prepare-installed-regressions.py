from pathlib import Path
import json,shutil

here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel223')
assert json.loads((here/'installed-control-validation.json').read_text())['all_capture_control_associations_verified']
text=(here.parent/'kernel220/run-standard-r7-client.py').read_text()
text=text.replace('wireplumber-reload-validation.json','coherent-install-validation.json').replace('new_r7_camera_libraries_loaded','coherent_driver_and_r8_r3_native_deployment')
text=text.replace('220','223').replace('installed-r7-standard-','installed-r8-standard-').replace('camera223-r7-client','camera223-r8-client')
compile(text,'standard-clients223','exec');(here/'run-standard-r8-client.py').write_text(text)
probes=private/'probes';probes.mkdir(mode=0o700,exist_ok=True)
source=private.parent/'kernel220/probes/gst-camera220-probe';target=probes/'gst-camera223-probe';assert not target.exists();shutil.copyfile(source,target)
proof=json.loads((here.parent/'kernel220/gst-client-build-validation.json').read_text());proof.update(stage=223,retained_prior_client_binary=True);(here/'gst-client-build-validation.json').write_text(json.dumps(proof,indent=2)+'\n')

text=(here.parent/'kernel220/capture-exposure-metadata.py').read_text().replace('220','223').replace('system-r7','system-r8').replace('camera223-r7','camera223-r8')
compile(text,'full-metadata223','exec');(here/'capture-full-metadata.py').write_text(text)
controller=(here.parent/'kernel219/full-mode-control.py').read_text().replace('stage=219','stage=223').replace('k219-runtime','k223-baseline').replace('k219-full-mode-experiment','k223-full-mode-experiment')
compile(controller,'full-mode-controller223','exec');(here/'native-full-mode-control.py').write_text(controller)
wrapper='''from pathlib import Path
import host,json,subprocess,sys
here=Path(__file__).resolve().parent
def control(action):
 p=host.ssh('python3 - '+action,input=(here/'native-full-mode-control.py').read_bytes(),timeout=65)
 (host.PRIVATE/('full-'+action+'-host-private.log')).write_bytes(p.stdout+p.stderr)
 r=json.loads(p.stdout);(here/('full-'+action+'-validation.json')).write_text(json.dumps(r,indent=2)+'\\n');print(json.dumps(r),flush=True)
control('start')
try:subprocess.run([sys.executable,str(here/'capture-full-metadata.py'),'4608','3456','system-r8'],check=True,timeout=110)
finally:control('finish')
for client in ['cam','gstreamer']:subprocess.run([sys.executable,str(here/'run-standard-r8-client.py'),client],check=True,timeout=110)
'''
compile(wrapper,'installed-regressions223','exec');(here/'run-installed-regressions.py').write_text(wrapper)

health=(here.parent/'kernel222/final-health.py').read_text().replace('k222-','k223-').replace('stage=222','stage=223').replace('k220-r7-package-candidates','k223-r8-package-candidates')
health=health.replace('r7_r2_camera_payload_records_verified','r8_r3_camera_payload_records_verified')
a=health.index('trials=[]');b=health.index('import struct,fcntl,re',a)
health=health[:a]+"""trials=[]
for name in ['k223-paired-sof-trial','k223-control-snapshot-trial']:
 r=json.loads((root/name/'state-private.json').read_text());assert r['phase']=='verified-restored';trials.append(name)
assert json.loads((root/'k223-r8-paired-deployment/state-private.json').read_text())['phase']=='verified'
assert json.loads((root/'k223-full-mode-experiment/state-private.json').read_text())['state']=='finished-default-mode-restored'
"""+health[b:]
health=health.replace('82cbc0528a76858ac57e149bdb540d14630112d74213384303960eead684fe58','fae1ed40da4e2751c081aca3a990a5a3c44de47599883a045340b9f62f54803e')
a=health.index(" try:fcntl.ioctl(fd,0x4020565a");b=health.index('\nfinally:os.close(fd)',a)
health=health[:a]+" fcntl.ioctl(fd,0x4020565a,sub,True)"+health[b:]
health=health.replace('original_camss_file_and_loaded_note_verified=True,candidate_frame_sync_not_left_enabled=True', 'deployed_camss_file_and_loaded_note_verified=True,standard_frame_sync_subscription_verified=True')
compile(health,'health223','exec');(here/'final-health.py').write_text(health)
archive=(here.parent/'kernel222/collect-final-evidence.py').read_text().replace('222','223').replace('kernel_module_backup_retained_in_prior219_archive=True','original_camss_backup_in_this_archive=True')
compile(archive,'evidence223','exec');(here/'collect-final-evidence.py').write_text(archive)
print('K223_INSTALLED_REGRESSIONS_HEALTH_AND_ARCHIVE_PREPARED')

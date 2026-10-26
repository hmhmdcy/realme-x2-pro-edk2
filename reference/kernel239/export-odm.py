"""Export only the selected ODM source files and metadata to private host storage."""
from pathlib import Path
import base64,hashlib,json
import host
R=Path(__file__).resolve().parent
assert json.loads((R/'odm-validation.json').read_text())['exit_code']==0
code=r'''
from pathlib import Path
import base64,json
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes();p=r/'k239-odm-source'
assert json.loads((p/'state-private.json').read_text())['exit_code']==0
manifest=json.loads((p/'files-manifest-private.json').read_text())
assert set(manifest)<={'etc/gps.conf','build.prop','etc/build.prop'}
metadata={name:json.loads((p/name).read_text()) for name in ['exact-paths-private.json','source-properties-private.json','geometry-private.json','summary.json']}
print(json.dumps(dict(manifest=manifest,metadata=metadata,payload={name:base64.b64encode((p/'payload'/name).read_bytes()).decode() for name in manifest})))
'''
result=host.ssh('python3 -',input=code.encode(),timeout=15);(host.PRIVATE/'odm-export-host-private.log').write_bytes(result.stdout+result.stderr);data=json.loads(result.stdout)
dest=host.PRIVATE/'odm-source-private';assert not dest.exists();dest.mkdir(mode=0o700)
for name,item in data['manifest'].items():
 assert name in ['etc/gps.conf','build.prop','etc/build.prop']
 body=base64.b64decode(data['payload'][name],validate=True);assert len(body)==item['bytes'] and hashlib.sha256(body).hexdigest()==item['sha256']
 target=dest/'payload'/name;target.parent.mkdir(parents=True,exist_ok=True,mode=0o700);target.write_bytes(body)
for name,item in data['metadata'].items():(dest/name).write_text(json.dumps(item,indent=2)+'\n')
(dest/'files-manifest-private.json').write_text(json.dumps(data['manifest'],indent=2)+'\n')
report=dict(stage=239,selected_source_files=len(data['manifest']),all_members_verified=True,gps_conf_actual_current_odm_exported=True,full_payload_and_fingerprints_private=True,no_gnss_action=True)
(R/'odm-export-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

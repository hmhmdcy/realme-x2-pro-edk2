"""Restore only the saved camera module files; pair with the recorded boot rollback."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
assert sys.argv[1:]==['--offline-files-only'],'Explicit disk-file rollback mode required'
root=Path('/var/lib/samurai/k390-deployment');records=json.loads((root/'rollback-files-private.json').read_text());meta=json.loads((root/'manifest.json').read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
dev=Path('/sys/bus/platform/devices/ac10000.icp')
if (dev/'state').exists():
 s=json.loads((dev/'state').read_text());q=json.loads((dev/'m2m_status').read_text())
 assert not any(q[k] for k in ['users','running','pinned','orphans'])
 assert not any(s[k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','mapped_bytes','ipe_dma_pending','imported_buffers'])
if Path('/sys/module/qcom_camss/refcnt').exists():assert Path('/sys/module/qcom_camss/refcnt').read_text().strip()=='0','Stop camera consumers first'
for r in records:
 p=Path(r['target']);assert not p.exists() or sha(p) in [r.get('old_sha256'),r['new_sha256']]
 if r['existed']:assert sha(root/'backup'/r['name'])==r['old_sha256']
for r in records:
 p=Path(r['target'])
 if r['existed']:
  tmp=p.with_name(p.name+'.k390-rollback-tmp');assert not tmp.exists()
  with tmp.open('xb') as f:f.write((root/'backup'/r['name']).read_bytes());f.flush();os.fsync(f.fileno())
  tmp.chmod(r['old_mode']);tmp.replace(p);assert sha(p)==r['old_sha256']
 elif p.exists():p.unlink()
q=subprocess.run(['depmod','-a',meta['release']],capture_output=True);assert not q.returncode,q.stderr.decode()
os.sync();print(json.dumps(dict(files_restored=True,loaded_code_not_switched=True,paired_boot_rollback_still_required=True)))

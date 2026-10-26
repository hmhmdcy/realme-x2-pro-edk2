from pathlib import Path
import hashlib,json,os,subprocess

root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k203-baseline/boot-id-private.txt').read_bytes()
out=root/'k203-package-records';assert not out.exists();out.mkdir(mode=0o700)
selected=[]
for entry in Path('/lib/apk/db/installed').read_text().split('\n\n'):
 metadata={line[:1]:line[2:] for line in entry.splitlines() if len(line)>1 and line[1]==':' and line[:1] in ['P','V','A','D','i','o','L','U','T','t','c','p','k','q','r']}
 if metadata.get('P','').startswith('modemmanager') or metadata.get('P')=='libmm-glib':
  selected.append(metadata);(out/(metadata['P']+'-record-private.txt')).write_text(entry+'\n\n')
(out/'metadata-private.json').write_text(json.dumps(selected,indent=2)+'\n')
candidate=root/'k191-mm-build/candidate/ModemManager';assert hashlib.sha256(candidate.read_bytes()).hexdigest()=='b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc'
(out/'ModemManager-candidate').write_bytes(candidate.read_bytes())
print(json.dumps(dict(stage=203,selected_metadata=selected,candidate191_exact=True)))

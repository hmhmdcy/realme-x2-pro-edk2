"""Read only the exact two already used config files; no helper or build."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
r=json.loads((HERE/'build-result.json').read_text())
original=Path('/mnt/samurai-full282/build/.config');private=Path(r['private_build'])/'.config'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
# Kconfig preserves the exact copied pre-sync input here. No need to restore
# a loop mount merely to compare text if its hash proves that same input.
shared=private.with_name('.config.old')
assert sha(shared)==r['shared_inputs_before'][str(original)]
assert sha(private)==r['private_configuration_sha256']
def values(p):
 active={};disabled=set()
 for line in p.read_text().splitlines():
  if line.startswith('CONFIG_'):
   k,v=line.split('=',1);active[k]=v
  elif line.startswith('# CONFIG_') and line.endswith(' is not set'):disabled.add(line[2:-11])
 return active,disabled
a,ad=values(shared);b,bd=values(private)
differences={k:dict(shared=a.get(k),private=b.get(k)) for k in sorted(a.keys()|b.keys()) if a.get(k)!=b.get(k)}
audit=dict(defined_configuration_values_unchanged=not differences,defined_configuration_differences=differences,
 disabled_comments_removed=sorted(ad-bd),disabled_comments_added=sorted(bd-ad),
 shared_sha256=sha(shared),private_sha256=sha(private),
 exact_prebuild_config_private=str(shared),original_shared_config=str(original),
 kernel_or_source_modified=False,configuration_written=False,tests_rerun=False,build_rerun=False)
(HERE/'configuration-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print(json.dumps(audit,indent=2))

"""Compare served MCFG source inventory with the original Android modem backup."""
from pathlib import Path
import hashlib,json,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel242')
snap=json.loads((P/'inspect-rf-firmware-private.json').read_text())['private']['snapshots']
manifest=json.loads(snap['/run/samurai-wifi/mcfg-state/source-manifest-private.json'])
backup=Path(json.loads((P/'android-backup-source-private.json').read_text())['modem_image'])
results={}
for name,v in manifest.items():
 assert name.startswith('modem_pr/mcfg/') and '..' not in Path(name).parts
 x=subprocess.run(['mtype','-i',str(backup),'::/image/'+name],capture_output=True)
 results[name]=dict(present=x.returncode==0,bytes=len(x.stdout),matches=x.returncode==0 and len(x.stdout)==v['bytes'] and hashlib.sha256(x.stdout).hexdigest()==v['sha256'])
report=dict(stage=242,mcfg_source_files_compared=len(results),all_byte_exact_to_original_android_backup=all(v['matches'] for v in results.values()),
 inventory_is_served_source_not_android_runtime_selected_config=True,read_only_host_comparison=True,no_pdc_load_select_activate=True,no_phone_changes=True)
(P/'mcfg-comparison-private.json').write_text(json.dumps(dict(report=report,files=results),indent=2)+'\n')
(R/'mcfg-comparison-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

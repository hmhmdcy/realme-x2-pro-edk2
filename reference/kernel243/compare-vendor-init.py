from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel243')
files=json.loads((P/'collect-vendor-init-private.json').read_text())['private'];rows=[]
for name,item in files.items():
 base=P/'rom-init'/('vendor_bin/bin' if name.startswith('bin/') else 'vendor_etc_init/init')
 q=base/(name[4:] if name.startswith('bin/') else name[9:])
 rows.append(dict(path=name,present=item['present'],rom_present=q.is_file(),same_hash=(hashlib.sha256(q.read_bytes()).hexdigest()==item['sha256']) if q.is_file() and item['present'] else None))
report=dict(stage=243,files=rows,all_present_selected_files_match=all(x['same_hash'] for x in rows if x['present']),missing_selected_in_both=sum(not x['present'] and not x['rom_present'] for x in rows))
(R/'vendor-init-comparison-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

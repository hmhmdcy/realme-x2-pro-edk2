from pathlib import Path
import json,re
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel243')
v=json.loads((P/'inspect-diag-and-pdc-private.json').read_text())['private'];current=v['pdc'];old=v['historical']['k207-pdc-queries-r2']
same={kind:current[kind+'-selected-private']['active_id']==old[kind+'-selected-private.json']['active_id'] for kind in ['platform','software']}
manifest=json.loads(json.loads((P.parent/'kernel242/inspect-rf-firmware-private.json').read_text())['private']['snapshots']['/run/samurai-wifi/mcfg-state/source-manifest-private.json'])
matches={}
for kind in ['platform','software']:
 info=current[kind+'-info-private'];ident=bytes.fromhex(current[kind+'-selected-private']['active_id'])
 candidates=[n for n,rec in manifest.items() if rec['bytes']==info['total_size']]
 matches[kind]=dict(description=info['description'],version=info['version'],size=info['total_size'],same_size_source_candidates=candidates,selected_id_utf8=ident.decode(errors='replace'))
(P/'pdc-runtime-comparison-private.json').write_text(json.dumps(dict(same_active_id_as207=same,metadata=matches),indent=2)+'\n')
report=dict(stage=243,same_active_platform_id_as207=same['platform'],same_active_software_id_as207=same['software'],platform_mbn_bytes=matches['platform']['size'],software_mbn_bytes=matches['software']['size'],
 platform_version=matches['platform']['version'],software_version=matches['software']['version'],both_have_same_size_source_candidates=all(matches[k]['same_size_source_candidates'] for k in matches),
 size_or_description_not_content_hash_proof=True,no_pdc_select_activate=True)
(R/'pdc-runtime-comparison-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

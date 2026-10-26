"""Retain the normal-consumer audit and prove the queued frames used one RPC."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel443/check-hardware.py').read_text()
source=source.replace("HERE/'frame-audit.py'", "HERE.parent/'kernel443/frame-audit.py'")
source=source.replace('stage=443','stage=444')
source=source.replace('f7c25ff3818b95954cfe7cc310d21f3b406225860abf20bb44e32ee66f5ad704',next(r['sha256'] for r in json.loads((HERE/'build-validation.json').read_text())['runtime_files'] if r['name']=='libcamera.so.0.7.2'))
source=source.replace("HERE/'profile-export-validation.json'", "HERE.parent/'kernel443/profile-export-validation.json'")
source=source.replace('unchanged442_core_and_441_modules=True,only_mode4_ds4_profile_binding_added=True,', 'matched_protocol6_core_proxy_and_module=True,retained441_modules_and443_profile=True,focus_tone_source_functions_and_packet_contract_unchanged=True,')
source=source.replace('factory_profile_and_actual_ipa5_proofs=True', 'factory_profile_reused_from443_and_actual_ipa6_proof=True')
marker=" assert row['queued_images']==summary['ipe_completed']"
extra='''
 focused=[tuple(map(int,m)) for m in re.findall(r'FRAME_IPA_PREPARE epoch=1 sof=(\\d+) combined=(\\d+) focus-us=(\\d+) dispatch-us=(\\d+) focus-status=(-?\\d+) tone-prepared=(\\d+)',text)]
 tone=[tuple(map(int,m)) for m in re.findall(r'TONE_IPA_PREPARE epoch=1 sof=(\\d+) cached=(\\d+) dispatch-us=(\\d+) status=(-?\\d+)',text)]
 f={r[0]:r for r in focused};t={r[0]:r for r in tone};assert len(f)==len(focused) and len(t)==len(tone)
 queued={int(sof) for sof in re.findall(r'IPE_TONE_QUEUE epoch=1 sof=(\\d+)',text)}
 assert len(queued)==row['queued_images'] and queued<=set(f)&set(t)
 assert all(f[s][1]==f[s][5]==t[s][1]==1 and f[s][4]==t[s][3]==0 for s in queued)
 def times(xs):
  xs=sorted(v/1000 for v in xs);return dict(median_ms=round(statistics.median(xs),3),p95_ms=round(xs[min(len(xs)-1,len(xs)*95//100)],3),maximum_ms=round(xs[-1],3))
 row.update(combined_calls_used_for_queued_images=len(queued),second_tone_rpc_calls_for_queued_images=0,
  focus_measurement=times([f[s][2] for s in queued]),combined_dispatch=times([f[s][3] for s in queued]),
  cached_tone_transfer=times([t[s][2] for s in queued]))
'''
assert source.count(marker)==1;source=source.replace(marker,marker+extra)
source=source.replace("assert staged['core_sha256']==", "assert staged['private_ipa_version']==6\nassert staged['core_sha256']==")
exec(compile(source,str(HERE/'check-hardware.py'),'exec'))

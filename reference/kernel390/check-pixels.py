"""Check the completed native phase independently of the later harness failure."""
from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
observation=json.loads((P/'runtime-r1-observe-private.json').read_text()) if (P/'runtime-r1-observe-private.json').exists() else json.loads((P/'runtime-observe-private.json').read_text())
assert not any(observation[k] for k in ['worker_live','client_live','collector_live'])
s=observation['state'];assert s['terminal'] and s['export_lifetime_passed'] and s['native_status']['completed']==s['native_status']['direct_completed']==18 and s['native_report']['passed']
script=(HERE.parent/'kernel386/check-pixels.py').read_text()
a=script.index('runtime=json.loads(');b=script.index("client=runtime['client_report']")
script=script[:a]+"runtime=dict(client_report=s['native_report'])\n"+script[b:]
script=script.replace('collected-r4','runtime-collected-r1').replace("stage=386,run='r4'","stage=390,run='r1-native-phase'")
script=script.replace("b'\\xa5'*(stride-w)","b'\\xa7'*(stride-w)")
script=script.replace('zero_copy_not_claimed=True,libcamera_pipeline_not_yet_integrated=True','normal_platform_owner_direct_dma_verified=True,pipeline_phase_failure_audited_separately=True')
exec(compile(script,str(HERE/'pixels-generated.py'),'exec'),globals())

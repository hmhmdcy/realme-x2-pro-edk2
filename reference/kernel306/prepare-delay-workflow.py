"""Create explicit current-boot variants without overwriting measured 301 tools."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
for name in ['launch-delay.py','poll-delay.py','native-delay.py','analyse-delay.py']:
 source=(HERE.parent/'kernel301'/name).read_text()
 source=source.replace('k301-delay-','k306-delay-').replace('stage=301','stage=306')
 source=source.replace('/var/lib/samurai/k298-work/boot-id-private.txt','/var/lib/samurai/k305-geometry-r2/boot-id-private.txt')
 if name=='native-delay.py':
  source=source.replace("str(stage/'bin/pipeline-smoke'),'imx319',str(stage/'bin/control-stepper')",
   "str(stage/'bin/pipeline-smoke'),'s5k3m5',str(stage/'bin/control-stepper')")
  source=source.replace("scene_wb_is_not_factory_awb=True","unity_wb_no_awb=True")
  source=source.replace("STEPPER_INITIAL_READBACK exposure=500 gain_code=512","STEPPER_INITIAL_READBACK exposure=500 gain_code=64")
  source=source.replace("and 'FIXTURE_RESULT result=0' in text","and 'FIXTURE_RESULT result=0' in text and 'FIXTURE_RESTORATION result=0' in text")
  source=source.replace("full_ipa_and_automatic_algorithms_not_implemented=True","test_bundle_uses300_manual_ipa=True")
  source=source.replace("measurement_only_no_delayed_controls_or_ae_implementation=True","measurement_bundle_does_not_assume_sensor_delays=True")
 if name=='analyse-delay.py':
  source=source.replace('no_delay_properties_committed=True,ae_or_awb_not_implemented=True',
   "no_delay_properties_committed=True,measurement_only=True,physical_sensor='s5k3m5',sensor_mode='2104x1560,481930000 pixelrate,9648 line,1663 min frame'")
 compile(source,str(HERE/name),'exec');(HERE/name).write_text(source)
print(json.dumps(dict(stage=306,current_boot_guard=True,original301_sources_preserved=True,workflow_generated=True)))

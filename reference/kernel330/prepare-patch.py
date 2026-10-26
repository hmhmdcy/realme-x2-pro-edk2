from pathlib import Path
import difflib,json
HERE=Path(__file__).resolve().parent
state=json.loads((HERE/'source-state.json').read_text());base=Path(state['baseline']);tree=Path(state['source'])
names=['src/ipa/libipa/'+n for n in ['awb_calibration.cpp','awb_calibration.h','meson.build']]
names+=['src/ipa/camss-vfe/'+n for n in ['white_balance_reference.cpp','white_balance_reference.h','camss.cpp','meson.build']]
names+=['src/libcamera/pipeline/camss-vfe/camss_vfe.cpp','src/libcamera/control_ids_core.yaml']
patch=[]
for name in names:
 before=(base/name).read_text() if (base/name).exists() else ''
 after=(tree/name).read_text()
 patch.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+name if before else '/dev/null',tofile='b/'+name))
(HERE/'0031-camss-calibrated-white-balance.patch').write_text(''.join(patch))
state.update(changed_sources=names,incremental_patch='0031-camss-calibrated-white-balance.patch',kernel_and_board_changes=False)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
print('Saved r26-based incremental core/IPA patch; package recipes and deployed defaults unchanged.')

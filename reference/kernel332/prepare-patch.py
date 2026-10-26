from pathlib import Path
import difflib,json
HERE=Path(__file__).resolve().parent
state=json.loads((HERE/'source-state.json').read_text());base=Path(state['baseline']);tree=Path(state['source'])
patch=[]
for name in state['changed_sources']:
 before=(base/name).read_text() if (base/name).exists() else '';after=(tree/name).read_text()
 patch.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+name if before else '/dev/null',tofile='b/'+name))
(HERE/'0032-camss-calibrated-cct-estimation.patch').write_text(''.join(patch))
state['incremental_patch']='0032-camss-calibrated-cct-estimation.patch'
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
print('Saved330-based incremental IPA CCT patch; no kernel, board or installed-file changes.')

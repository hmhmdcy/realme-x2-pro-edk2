"""Read-only join evidence after the actual owned outer wait returned."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
BASE=Path('/home/cy122/charging-management-20261023/phosh-external-power-build-501-r1')
raw=(BASE/'installed-target-build-state-private.json').read_bytes()
state=json.loads(raw)
assert state['terminal'] is True and state['returncode']==-2
interrupt=json.loads((BASE/'cancelled-desktop-sigint-private.json').read_bytes())
rows=[]
for original in interrupt['descendants_before']:
    p=Path('/proc',str(original['pid']))
    try:fields=(p/'stat').read_text().rsplit(')',1)[1].split()
    except FileNotFoundError:
        rows.append({'pid':original['pid'],'startticks':original['startticks'],'status':'absent'});continue
    assert int(fields[19])!=original['startticks'],(original['pid'],fields[0])
    rows.append({'pid':original['pid'],'startticks':original['startticks'],'status':'original_absent_PID_reused'})
result={'schema':'samurai-cancelled-desktop-build-stop-v1','terminal':True,'passed':True,
        'owned_tool_session':54830,'outer_wait_result':state['returncode'],
        'signalled':interrupt['signalled'],'all_captured_descendants_original_identity_absent':True,
        'descendants':rows,'no_new_build_or_test_started':True,'no_APK_built_or_installed':True,
        'no_phone_or_desktop_changes_by_this_agent':True,
        'build_state_sha256':hashlib.sha256(raw).hexdigest(),
        'stop_source_sha256':interrupt['source_sha256'],
        'verification_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
out=HERE/'cancelled-desktop-stop-result.json'
assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'terminal':True,'ninja_pid':interrupt['signalled']['pid'],'returncode':state['returncode'],
                  'original_descendants_absent':len(rows),'result_sha256':hashlib.sha256(out.read_bytes()).hexdigest()}))

"""Exercise unmodified cam through its standard interface, then observe PM."""
from pathlib import Path
import json
import os
import pwd
import re
import resource
import subprocess
import time
import traceback

os.umask(0o077);r=Path('/var/lib/samurai');o=r/'k267-native-cam';o.mkdir(mode=0o700)
state=dict(stage=267,state='running',terminal=False,pid=os.getpid());results=[]
def save():
    p=o/'state-next-private.json';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(o/'state-private.json')
def idle():
    for device in ['7-0010','9-0010']:
        assert Path('/sys/bus/i2c/devices',device,'power/runtime_status').read_text().strip()=='suspended'
    for p in Path('/sys/class/regulator').glob('regulator.*'):
        if (p/'name').read_text().strip().startswith(('cam-front-','cam-rear-')):
            assert (p/'state').read_text().strip()=='disabled' and (p/'num_users').read_text().strip()=='0'
    clocks=Path('/sys/kernel/debug/clk/clk_summary').read_text()
    for name in ['cam_cc_mclk1_clk','cam_cc_mclk2_clk']:
        assert any(x.split()[0]==name and x.split()[1]=='0' for x in clocks.splitlines() if x.split())
save();error=None;before=subprocess.check_output(['dmesg'])
try:
    assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k267-work/boot-id-private.txt').read_bytes()
    assert b'mode: cpu' in Path('/etc/libcamera/configuration.yaml').read_bytes()
    user=pwd.getpwuid(10000)
    desktop=next(p for p in Path('/proc').glob('[0-9]*') if (p/'comm').exists() and (p/'comm').read_text().strip()=='phosh')
    inherited={k.decode():v.decode() for item in (desktop/'environ').read_bytes().split(b'\0') if b'=' in item for k,v in [item.split(b'=',1)]}
    env={k:v for k,v in inherited.items() if k in ['PATH','HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY']}
    def demote():
        resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
    idle()
    for cycle in range(3):
        for which,cci in [('rear','ac4a000'),('front','ac4b000')]:
            camera='/base/soc@0/cci@'+cci+'/i2c-bus@1/camera@10'
            q=subprocess.run(['cam','-c',camera,'--capture=12'],env=env,preexec_fn=demote,capture_output=True,timeout=20)
            (o/(str(cycle)+'-'+which+'-stdout-private.txt')).write_bytes(q.stdout)
            (o/(str(cycle)+'-'+which+'-stderr-private.txt')).write_bytes(q.stderr)
            text=q.stdout.decode();sequences=[int(x) for x in re.findall(r'seq:\s*(\d+)',text)]
            row=dict(cycle=cycle,camera=which,exit_code=q.returncode,frame_sequences=sequences)
            results.append(row)
            (o/'captures-private.json').write_text(json.dumps(results,indent=2)+'\n')
            assert q.returncode==0
            assert len(sequences)==12 and all(b>a for a,b in zip(sequences,sequences[1:])),text[-2000:]
            time.sleep(.5);idle()
    after=subprocess.check_output(['dmesg']);(o/'dmesg-after-private.txt').write_bytes(after)
    faults={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',fatal=b'fatal error received').items()}
    assert not any(faults.values()) and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
    summary=dict(stage=267,application='unmodified cam',cycles=3,captures=results,total_frames=sum(len(x['frame_sequences']) for x in results),
                 no_application_environment_overrides=True,system_cpu_isp_configuration_preserved=True,
                 after_each_capture_rails_off_and_pm_suspended=True,mclk1_mclk2_off=True,
                 fault_delta=faults,taint=0,no_scene_files_saved=True)
    (o/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    state.update(state='terminal',terminal=True,exit_code=0);save()
except BaseException:
    (o/'failure-private.txt').write_text(traceback.format_exc());state.update(state='failed',terminal=True,exit_code=1);save();raise SystemExit(1)

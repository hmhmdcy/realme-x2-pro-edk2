"""Install the hash-bound Image505 trial from its private phone staging directory."""
from pathlib import Path
import fcntl,importlib.util,json,os,subprocess,sys,traceback
ROOT=Path('/root/charging-management-20261023/tcpm507-trial-20261025-02')
spec=importlib.util.spec_from_file_location('image505_trial_guard',ROOT/'new/usr/lib/samurai-charging/tcpm507-boot-guard.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
os.umask(0o077);assert os.geteuid()==0
lock=os.open(ROOT/'stage.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600);fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert not (ROOT/'stage-result.json').exists() and not (ROOT/'stage-began.json').exists()
meta=g.load();assert g.boot()==meta['source_boot']
ready=json.loads((ROOT/'full-pd-shutdown-ready.json').read_bytes())
assert ready['passed'] and ready['parts']=={name:row['new'] for name,row in meta['parts'].items()},'full PD shutdown closure not verified'
assert '#506 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026' in Path('/proc/version').read_text()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='4096'
for path,row in meta['files'].items():assert g.target_hash(path)==(row['old']['sha256'] if row['old'] else None),path
for name in ['boot','logdump']:assert g.digest(g.PARTS[name][0])==meta['parts'][name]['old']
sample={k:int(v) for k,v in (word.split('=') for word in Path('/sys/bus/i2c/devices/0-005c/telemetry').read_text().split())}
assert sample['valid']==sample['online']==sample['protection_ok']==1
assert all(sample[key]==0 for key in ['latched','stop_error','error','fault','thermal_inhibit','cycle_timeout'])
assert 100<=sample['temp_decic']<=400 and max(sample['cell1_uv'],sample['cell2_uv'])<=4375000
# The ongoing real discharge/precharge transaction must be finished first.
experiment=Path('/root/charging-management-20261023/precharge506-live-20261025-02')
outcome=json.loads((experiment/'result-private.json').read_bytes())
assert outcome['auto_restored'] and outcome['error'] is None and outcome['cleanup_error'] is None
closed=json.loads((experiment/'supervisor-terminal.json').read_bytes())
assert closed['child_joined'] and closed['auto_restored'] and closed['returncode']==0 and closed['cleanup_error'] is None
for pid,start in [(11217,275499),(11218,275509),(11223,275599),(11224,275599),(11225,275600),(18739,643837)]:
    info=Path('/proc',str(pid),'stat')
    if info.exists():
        fields=info.read_text().rsplit(')',1)[1].split()
        assert int(fields[19])!=start,(pid,'original test still active')
assert '[auto]' in Path('/sys/class/power_supply/mp2650-input/charge_behaviour').read_text()
assert int(Path('/sys/class/power_supply/bq28z610-0/capacity').read_text())>=20
assert min(sample['cell1_uv'],sample['cell2_uv'])>=3700000

g.atomic(ROOT/'stage-began.json',json.dumps(dict(boot=g.boot(),pid=os.getpid(),sample=sample)).encode())
result=dict(passed=False,old_boot=g.boot(),partition_order=[],files_changed=[])
try:
    stopped=subprocess.run(['/usr/sbin/samurai-charging','stop'],capture_output=True,text=True,timeout=20)
    assert stopped.returncode==0,(stopped.returncode,stopped.stderr)
    result['ordinary_service_stop']=json.loads(stopped.stdout)
    for name in ['logdump','boot']:
        g.write_part(meta,name,'new');result['partition_order'].append(name)
    # The helper exists before its OpenRC caller; the manifest is installed last.
    order=sorted(meta['files'],key=lambda path:(path=='/usr/share/samurai-charging/manifest.json',path=='/etc/init.d/samurai-charging'))
    for path in order:
        row=meta['files'][path]['new']
        if g.target_hash(path)==row['sha256']:continue
        g.atomic(path,(ROOT/'new'/path.lstrip('/')).read_bytes(),row['mode'])
        assert g.digest(path)==row['sha256'];result['files_changed'].append(path)
    for path,row in meta['files'].items():assert g.digest(path)==row['new']['sha256']
    for name in ['boot','logdump']:assert g.digest(g.PARTS[name][0])==meta['parts'][name]['new']
    result.update(passed=True,installed=True,reboot_requested=True,hot_module_unload=False,old_loaded_input_note=g.digest('/sys/module/samurai_usb_input/notes/.note.gnu.build-id'))
    g.atomic(ROOT/'stage-result.json',(json.dumps(result,indent=2)+'\n').encode());os.sync()
    subprocess.run(['/sbin/reboot'],check=True,timeout=20)
except BaseException as error:
    result.update(error=repr(error),traceback=traceback.format_exc())
    try:
        g.rollback(meta,'stage-error',False)
        resumed=subprocess.run(['/usr/sbin/samurai-charging','resume'],capture_output=True,text=True,timeout=20)
        result['recovery_resume']=dict(returncode=resumed.returncode,stdout=resumed.stdout,stderr=resumed.stderr)
    except BaseException as recovery_error:result['recovery_error']=repr(recovery_error)
    g.atomic(ROOT/'stage-result.json',(json.dumps(result,indent=2)+'\n').encode());raise

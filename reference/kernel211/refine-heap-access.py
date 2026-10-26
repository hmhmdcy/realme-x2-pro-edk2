from pathlib import Path
import errno,grp,hashlib,json,os,pwd,shutil,stat,subprocess,sys
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k211-baseline/boot-id-private.txt').read_bytes()
out=root/'k211-heap-access-refine';out.mkdir(mode=0o700)
target=Path('/etc/udev/rules.d/70-samurai-camera-heaps.rules');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
original=json.loads((root/'k211-heap-stage/source-manifest.json').read_text())['70-samurai-camera-heaps.rules'];assert sha(target)==original
shutil.copyfile(target,out/'broad-rule-before-private.rules')
new=root/'k211-heap-stage/70-samurai-camera-heaps-scoped.rules';data=new.read_bytes();assert b'fastrpc-shared-pool' in data and b'KERNEL==' in data
temporary=target.with_name(target.name+'.k211-scoped');assert not temporary.exists();temporary.write_bytes(data);temporary.chmod(0o644);os.replace(temporary,target)
for i,args in enumerate([['udevadm','control','--reload-rules'],['udevadm','trigger','--subsystem-match=dma_heap','--action=change'],['udevadm','settle','--timeout=10']]):
    p=subprocess.run(args,capture_output=True,timeout=20);(out/('command-'+str(i)+'-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0
protected=Path('/dev/dma_heap/fastrpc-shared-pool');assert protected.exists()
# Clear any access mask left by the first, broader rule after removing its tag.
os.chown(protected,0,0);os.chmod(protected,0o600)
st=protected.stat();assert st.st_uid==st.st_gid==0 and stat.S_IMODE(st.st_mode)==0o600
info=subprocess.check_output(['udevadm','info','--query=property','--name='+str(protected)],text=True);(out/'protected-udev-private.txt').write_text(info)
assert not any('uaccess' in l for l in info.splitlines() if l.startswith(('TAGS=','CURRENT_TAGS=')))
user=pwd.getpwuid(10000)
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
program=r'''
import errno,json,os
accessible=[]
for name in ['system','reserved','default_cma_region']:
    fd=os.open('/dev/dma_heap/'+name,os.O_RDWR|os.O_CLOEXEC);os.close(fd);accessible.append(name)
try:fd=os.open('/dev/dma_heap/fastrpc-shared-pool',os.O_RDWR|os.O_CLOEXEC)
except OSError as error:assert error.errno==errno.EACCES
else:os.close(fd);raise AssertionError('Dedicated DSP pool accessible to camera user')
print(json.dumps(dict(uid=os.geteuid(),camera_heaps_accessible=accessible,dedicated_dsp_pool_access_denied=True)))
'''
p=subprocess.run([sys.executable,'-c',program],preexec_fn=demote,cwd='/',capture_output=True,timeout=15);(out/'user-access-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
report=dict(stage=211,rule_scoped_to_general_camera_heaps=True,initial_broad_rule_replaced=True,protected_dsp_pool_root_only=True,protected_dsp_pool_never_allocated_by_test=True,user_access=json.loads(p.stdout),source_rule_sha256=sha(target),sensor_still_suspended=Path('/sys/bus/i2c/devices/7-0010/power/runtime_status').read_text().strip()=='suspended')
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

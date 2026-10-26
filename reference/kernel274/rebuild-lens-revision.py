from pathlib import Path
import hashlib,json,os,shutil,subprocess,time
import host
R=Path(__file__).resolve().parent;W=Path('/home/cy122/x2pro-linux/camera270-kernel');B=Path('/home/cy122/x2pro-linux/camera274-build-r1')
old=json.loads((R/'driver-build-validation.json').read_text());assert old['attempt']==1 and old['sensor_w1_diagnostics']==0
test=json.loads((R/'lens-callback-validation.json').read_text());source=(R/'lc898219xi.c').read_bytes();sha=hashlib.sha256(source).hexdigest();assert sha==test['source_sha256'] and test['passed']
(host.PRIVATE/'driver-build-revision1-validation.json').write_text(json.dumps(old,indent=2)+'\n');shutil.copyfile(R/'lc898219xi.c',W/'drivers/media/i2c/lc898219xi.c')
env=dict(os.environ,PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup',KBUILD_BUILD_VERSION='274',KBUILD_BUILD_USER='builder',KBUILD_BUILD_HOST='samurai')
start=time.monotonic();q=subprocess.run(['make','-C',str(W),'O='+str(B),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory','-j3','W=1','drivers/media/i2c/lc898219xi.o'],env=env,capture_output=True)
(host.PRIVATE/'lens-revision2-build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr).decode()
diagnostics=[l for l in (q.stdout+q.stderr).decode().splitlines() if 'warning:' in l.lower() or 'error:' in l.lower()];assert not diagnostics,diagnostics
old.update(revision=2,source_sha256=sha,object_sha256=hashlib.sha256((B/'drivers/media/i2c/lc898219xi.o').read_bytes()).hexdigest(),revision2_seconds=round(time.monotonic()-start,2))
(R/'driver-build-validation.json').write_text(json.dumps(old,indent=2)+'\n')
p=R/'lens-candidate-source-validation.json';d=json.loads(p.read_text());d['source_sha256']=sha;d['actual_callbacks_host_test_cases']=test['actual_callback_cases'];p.write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(dict(stage=274,revision=2,w1_diagnostics=0,source_sha256=sha,object_sha256=old['object_sha256'],not_deployed=True),indent=2))

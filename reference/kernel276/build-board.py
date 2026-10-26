from pathlib import Path
import hashlib,json,os,shutil,subprocess
import host
R=Path(__file__).resolve().parent;W=Path('/home/cy122/x2pro-linux/camera270-kernel');B=Path('/home/cy122/x2pro-linux/camera276-build-r1');B.mkdir(mode=0o700)
shutil.copyfile('/home/cy122/x2pro-linux/camera274-build-r1/.config',B/'.config')
env=dict(os.environ,PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup',KBUILD_BUILD_VERSION='276')
base=['make','-C',str(W),'O='+str(B),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','-j3']
for name,args in [('configure',['olddefconfig']),('board',['qcom/sm8150-samurai.dtb'])]:
 with (B/(name+'-private.log')).open('xb') as log:q=subprocess.run(base+args,env=env,stdout=log,stderr=subprocess.STDOUT)
 assert q.returncode==0,'Inspect '+name+' log'
dtb=B/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb';d=dict(stage=276,board_build_passed=True,dtb_sha256=hashlib.sha256(dtb.read_bytes()).hexdigest(),phone_unchanged=True)
(R/'board-build-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))

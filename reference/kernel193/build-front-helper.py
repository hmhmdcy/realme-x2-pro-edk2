from pathlib import Path
import hashlib,json,os,re,resource,shutil,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel193')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();source=json.loads((ref/'front-helper-source-validation.json').read_text());assert source['checkpatch_exit']==0 and sha(k/'drivers/of/samurai-front-identify.c')==source['helper_source_sha256']
before={p:sha(k/p) for p in ['.config','arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb']};assert all(sha(k/p)==digest for p,digest in source['previous14_source_hashes'].items())
symbols=(k/'Module.symvers').read_bytes();order=(k/'modules.order').read_bytes();assert len(symbols.splitlines())==16793 and len(order.splitlines())==770
original_config=(k/'.config').read_bytes();(out/'config-before-private').write_bytes(original_config)
(out/'full183-Module.symvers-before-private').write_bytes(symbols);(out/'full183-modules.order-before-private').write_bytes(order)
env=dict(os.environ,KBUILD_BUILD_VERSION='183',PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup')
def limit():resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
log=out/'front-helper-build-r4-private.log'
try:
 # Seed the new option as disabled so syncconfig cannot prompt on stdin.
 (k/'.config').write_bytes(original_config+b'\n# CONFIG_OF_SAMURAI_CCI_BRINGUP is not set\n# CONFIG_OF_SAMURAI_FRONT_IDENTIFY is not set\n')
 with log.open('xb') as stream:subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory','CONFIG_OF_SAMURAI_FRONT_IDENTIFY=m','W=1','-j3','drivers/of/samurai-front-identify.ko'],cwd=k,env=env,stdout=stream,stderr=subprocess.STDOUT,preexec_fn=limit,check=True)
finally:
 (k/'.config').write_bytes(original_config)
 (k/'Module.symvers').write_bytes(symbols);(k/'modules.order').write_bytes(order)
assert not re.findall(r'^.*\b(?:warning|error):.*$',log.read_text(),re.M)
candidate=out/'samurai-front-identify-k193r3-private.ko';assert not candidate.exists();shutil.copyfile(k/'drivers/of/samurai-front-identify.ko',candidate)
subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(candidate)],check=True)
vm=subprocess.check_output(['modinfo','-F','vermagic',str(candidate)],text=True).strip();assert vm==subprocess.check_output(['modinfo','-F','vermagic',str(k/'drivers/misc/fastrpc.ko')],text=True).strip()
imports=subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(candidate)],text=True);available={l.split()[1] for l in symbols.decode().splitlines()};assert all(l.split()[-1] in available for l in imports.splitlines() if l.strip())
intree=subprocess.check_output(['modinfo','-F','intree',str(candidate)],text=True).strip();assert intree=='Y'
assert all(sha(k/p)==digest for p,digest in before.items()) and all(sha(k/p)==digest for p,digest in source['previous14_source_hashes'].items())
record=dict(stage=193,helper_source_sha256=source['helper_source_sha256'],candidate_sha256=sha(candidate),candidate_bytes=candidate.stat().st_size,vermagic=vm,all_imports_in183_kernel=True,w1_warnings=0,existing14_sources_unchanged=True,image_dtb_config_unchanged=True,full_symvers_and_order_restored=True,built_via_in_tree_kbuild=True,manual_intree_metadata=False,runtime_loaded=False)
(ref/'front-helper-build-validation.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))

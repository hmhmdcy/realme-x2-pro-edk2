from pathlib import Path
import hashlib,json,os,re,resource,shutil,subprocess

k=Path('/home/cy122/pmos-samurai-kernel136/kernel');here=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel205');sha=lambda b:hashlib.sha256(b).hexdigest()
old=(k/'.config.old').read_bytes();current=(k/'.config').read_bytes();assert sha(old)=='55f1f0a35bd4f20ad70ebd383a8863e05d0b6d53a07c0f0f09fb47cee057913a'
old_enabled={l for l in old.decode().splitlines() if l.startswith('CONFIG_')};new_enabled={l for l in current.decode().splitlines() if l.startswith('CONFIG_')};assert old_enabled==new_enabled
added=set(current.decode().splitlines())-set(old.decode().splitlines());assert len(added)==5 and all(l.startswith('# CONFIG_OF_SAMURAI_') and l.endswith(' is not set') for l in added)
cfg=out/'diagnostic-build-config-private';assert not cfg.exists();cfg.write_bytes(current);(out/'original-config-private').write_bytes(old);(k/'.config').write_bytes(old)
sym=(k/'Module.symvers').read_bytes();order=(k/'modules.order').read_bytes();assert len(sym.splitlines())==16793 and len(order.splitlines())==770
env=dict(os.environ,KCONFIG_CONFIG=str(cfg),KCONFIG_NOSILENTUPDATE='1',KBUILD_BUILD_VERSION='183',PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup')
def limit():resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
try:
 with (out/'diagnostic-build-r2-private.log').open('xb') as log:subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory','W=1','-j3','drivers/bluetooth/btbcm.ko','drivers/bluetooth/btqca.ko','drivers/bluetooth/hci_uart.ko'],cwd=k,env=env,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limit,check=True)
finally:
 (k/'Module.symvers').write_bytes(sym);(k/'modules.order').write_bytes(order)
log=(out/'diagnostic-build-r2-private.log').read_text();assert not re.search(r'warning:|error:|Error in reading|Restart config',log,re.I),log[-1500:]
candidate=out/'hci_uart-k205-diagnostic-r2-private.ko';assert not candidate.exists();shutil.copyfile(k/'drivers/bluetooth/hci_uart.ko',candidate);subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(candidate)],check=True)
vm=subprocess.check_output(['modinfo','-F','vermagic',str(candidate)],text=True).strip();assert vm==subprocess.check_output(['modinfo','-F','vermagic',str(out/'hci_uart-before-build-private.ko')],text=True).strip()
symbols={l.split()[1] for l in sym.decode().splitlines()};undefined=subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(candidate)],text=True);assert all(l.split()[-1] in symbols for l in undefined.splitlines() if l.strip())
assert (k/'.config').read_bytes()==old and sha((k/'arch/arm64/boot/Image').read_bytes())=='bfa72dd920c8376ceefc458fe7202a73ddb364b6727556471d70c8d0e7ade469' and sha((k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb').read_bytes())=='22c1f2ad3c54c52f181c43d343840dc026a05aab499c8fac13dc2476ddded9d3'
source=json.loads((here/'diagnostic-source-validation.json').read_text())
r=dict(stage=205,kernel_build_unchanged=183,candidate_sha256=sha(candidate.read_bytes()),candidate_bytes=candidate.stat().st_size,source_sha256=source['source_after_sha256'],vermagic=vm,w1_diagnostics=0,imports_match_full183_symbols=True,full_symbols_and_order_restored=True,image_config_canonical_dtb_unchanged=True,all_enabled_build_configuration_values_unchanged=True,private_build_config_only_adds_five_disabled_fixture_options=True,first_syncconfig_prompt_failure_preserved=True,original_config_exactly_restored=True,runtime_deployed=False,diagnostics_only=True)
(here/'diagnostic-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))

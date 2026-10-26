from pathlib import Path
import hashlib,json,os,re,resource,shutil,subprocess

k=Path('/home/cy122/pmos-samurai-kernel136/kernel');here=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel205');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((here/'diagnostic-source-validation.json').read_text());assert sha(k/'drivers/bluetooth/hci_qca.c')==r['source_after_sha256']
expected=json.loads((here.parent/'kernel204/source-final-validation.json').read_text());assert all(sha(k/n)==h for n,h in expected['previous_source_sha256'].items());assert sha(k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts')==expected['board_dts_sha256']
before={n:sha(k/n) for n in ['.config','arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb']};sym=(k/'Module.symvers').read_bytes();order=(k/'modules.order').read_bytes();assert len(sym.splitlines())==16793 and len(order.splitlines())==770
(out/'full-symbols-before-private').write_bytes(sym);(out/'full-order-before-private').write_bytes(order)
shutil.copyfile(k/'drivers/bluetooth/hci_uart.ko',out/'hci_uart-before-build-private.ko')
env=dict(os.environ,KBUILD_BUILD_VERSION='183',PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup')
def limit():resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
try:
 with (out/'diagnostic-build-private.log').open('xb') as log:subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory','W=1','-j3','drivers/bluetooth/btbcm.ko','drivers/bluetooth/btqca.ko','drivers/bluetooth/hci_uart.ko'],cwd=k,env=env,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limit,check=True)
finally:
 (k/'Module.symvers').write_bytes(sym);(k/'modules.order').write_bytes(order)
log=(out/'diagnostic-build-private.log').read_text();diagnostics=re.findall(r'^.*\b(?:warning|error):.*$',log,re.M);assert not diagnostics,diagnostics
candidate=out/'hci_uart-k205-diagnostic-private.ko';assert not candidate.exists();shutil.copyfile(k/'drivers/bluetooth/hci_uart.ko',candidate);subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(candidate)],check=True)
vermagic=subprocess.check_output(['modinfo','-F','vermagic',str(candidate)],text=True).strip();assert vermagic==subprocess.check_output(['modinfo','-F','vermagic',str(out/'hci_uart-before-build-private.ko')],text=True).strip()
undefined=subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(candidate)],text=True);symbols={l.split()[1] for l in sym.decode().splitlines()};assert all(l.split()[-1] in symbols for l in undefined.splitlines() if l.strip())
assert all(sha(k/n)==h for n,h in before.items())
report=dict(stage=205,kernel_build_unchanged=183,candidate_sha256=sha(candidate),candidate_bytes=candidate.stat().st_size,source_sha256=r['source_after_sha256'],vermagic=vermagic,w1_diagnostics=0,imports_match_full183_symbols=True,full_symbols_and_order_restored=True,image_config_canonical_dtb_unchanged=True,runtime_deployed=False,diagnostics_only=True)
(here/'diagnostic-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

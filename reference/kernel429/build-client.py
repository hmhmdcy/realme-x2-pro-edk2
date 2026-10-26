from pathlib import Path
import hashlib,importlib.util,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
k=m.mounted_build().parent/'source354';inc=P/'includes/linux';inc.mkdir(parents=True,exist_ok=True)
shutil.copyfile(k/'include/uapi/linux/qcom-ipe-a5.h',inc/'qcom-ipe-a5.h')
q=subprocess.run(['aarch64-linux-gnu-gcc','-static','-O2','-Wall','-Wextra','-Werror','-I'+str(inc.parent),str(HERE/'pd10-ipe.c'),'-o',str(P/'pd10-ipe')],capture_output=True)
(P/'client-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
capture=P.parent/'kernel428/capture-collected-r6/s5kgw1-scene'
common=sorted(set(int(x.stem.split('-')[1]) for x in capture.glob('full-*.bin'))&set(int(x.stem.split('-')[1]) for x in capture.glob('ds4-*.bin')));seq=common[-1]
for src,dest in [(capture/f'full-{seq}.bin','full-private.bin'),(capture/f'ds4-{seq}.bin','pd10-private.bin'),(P.parent/'kernel424/factory-contract-private.bin','parameters-private.bin')]:shutil.copyfile(src,P/dest)
r=dict(stage=429,static_arm64=True,werror=True,source_sha256=hashlib.sha256((HERE/'pd10-ipe.c').read_bytes()).hexdigest(),probe_sha256=hashlib.sha256((P/'pd10-ipe').read_bytes()).hexdigest(),
 same_sof_full_pd10_source_stage=428,source_model='s5kgw1',source_sequence=seq,stock_ltm_packet_source_stage=424,
 modes=['real PD10','neutral black counterfactual PD10','neutral white counterfactual PD10','repeat real PD10'],
 full_input_constant_across_modes=True,no_new_live_sensor_capture_claimed=True,passed=True)
(HERE/'client-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))

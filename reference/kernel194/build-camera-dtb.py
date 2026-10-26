from pathlib import Path
import hashlib,subprocess,json
ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel194');k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
source=ref/'sm8150-samurai-camera-warm.dts';pre=out/'sm8150-samurai-camera-warm-private.pp';dtb=out/'sm8150-samurai-camera-warm-private.dtb'
cmd=['aarch64-linux-gnu-gcc','-E','-P','-nostdinc','-undef','-D__DTS__','-x','assembler-with-cpp','-I'+str(k/'arch/arm64/boot/dts/qcom'),'-I'+str(k/'arch/arm64/boot/dts'),'-I'+str(k/'scripts/dtc/include-prefixes'),'-I'+str(k/'include'),str(source),'-o',str(pre)]
subprocess.run(cmd,check=True,capture_output=True)
run=subprocess.run([str(k/'scripts/dtc/dtc'),'-@','-I','dts','-O','dtb','-o',str(dtb),str(pre)],capture_output=True,text=True);(out/'camera-dtc-private.log').write_text(run.stdout+run.stderr);assert run.returncode==0,run.stderr
record=dict(stage=194,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),dtb_sha256=hashlib.sha256(dtb.read_bytes()).hexdigest(),dtb_bytes=dtb.stat().st_size,symbols_enabled=True,canonical_board_dtb_overwritten=False,partial_pmic_inputs_intentionally_unmodelled=True,ready_for_upstream=False,hardware_deployed=False)
(ref/'camera-dtb-build-validation.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))

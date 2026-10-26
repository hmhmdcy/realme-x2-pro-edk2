from pathlib import Path
import re,json,hashlib,runpy
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py')
down=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source')
k=Path('/home/cy122/pmos-samurai-kernel118/camera120/kernel')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel120')
clean=lambda text:re.sub(r'/\*.*?\*/|//[^\n]*','',text,flags=re.S)
camera=clean((down/'arch/arm64/boot/dts/19781/sm8150-camera.dtsi').read_text())
driver=(k/'drivers/i2c/busses/i2c-qcom-cci.c').read_text()
generic=driver.split('static const struct cci_data cci_v2_data = {',1)[1].split('static const struct cci_data',1)[0]
fields=['thigh','tlow','tsu_sto','tsu_sta','thd_dat','thd_sta','tbuf','scl_stretch_en','trdhld','tsp']
results=[]
for ctrl in [0,1]:
    for mode,cpp in [('standard','STANDARD'),('fast','FAST'),('fast_plus','FAST_PLUS')]:
        body=re.search(r'i2c_freq_[^\n]+_cci'+str(ctrl)+r': qcom,i2c_'+mode+r'_mode\s*\{(.*?)\};',camera,re.S).group(1)
        own={key:int(re.search(r'hw-'+key.replace('_','-')+r'\s*=\s*<(\d+)>',body).group(1)) for key in fields}
        baseline_body=re.search(r'\.params\[I2C_MODE_'+cpp+r'\]\s*=\s*\{(.*?)\}',generic,re.S).group(1)
        base={key:int(re.search(r'\.'+key+r'\s*=\s*(\d+)',baseline_body).group(1)) for key in fields}
        diff={key:dict(native=own[key],generic=base[key]) for key in fields if own[key]!=base[key]}
        results.append(dict(controller=ctrl,mode=mode,fields_compared=len(fields),differences=diff))
assert all(not r['differences'] for r in results if r['mode']=='standard')
pmic=down/'arch/arm64/boot/dts/19781/pm8008.dtsi';mtp=down/'arch/arm64/boot/dts/19781/sm8150-mtp.dtsi'
text=clean(pmic.read_text())
assert '#include "pm8008.dtsi"' in mtp.read_text().split('&qupv3_se4_i2c {',1)[1].split('};',1)[0]
assert '<&pm8150l_gpios 1 0x00>' in text and '<&pm8150l_gpios 4 0x00>' in text
labels=re.findall(r'\b(L[1-7][PQ]):',text);assert len(labels)==14
assert 'interrupts' not in text
report=dict(timing_comparisons=results,standard_100khz_matches_20_fields=True,cci_source_clock_hz=37500000,camera_pmic_i2c_controller='QUPv3 SE4 / mainline i2c4',pmic_primary_and_secondary_addresses=[[8,9],[4,5]],pmic_reset_pins=[dict(controller='PM8150L',gpio=1),dict(controller='PM8150L',gpio=4)],pm8008_regulator_labels=labels,downstream_pmic_no_irq_description=True,current_mfd_irq_required=True,pmic_input_supplies_unresolved=True,physical_pmic_presence_not_probed=True,primary_optional_irq_references=['https://lkml.iu.edu/hypermail/linux/kernel/2609.1/01450.html','https://lkml.iu.edu/2609.2/08693.html'],source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [pmic,mtp]},phone_not_changed=True)
(ref/'cci-timing-and-pmic-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

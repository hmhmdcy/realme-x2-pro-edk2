from pathlib import Path
root=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source')
for fn in ['arch/arm64/boot/dts/19781/pm8008.dtsi','arch/arm64/boot/dts/19781/sm8150-camera-sensor-mtp.dtsi']:
 p=root/fn;print(fn)
 lines=p.read_text().splitlines()
 if fn.endswith('pm8008.dtsi'): print('\n'.join(lines))
 else:
  for i,s in enumerate(lines):
   if any(x in s for x in ['cam_sensor','gpio-custom','qcom,cam-custom','cam-vreg-name','qcom,cci-master','qcom,sensor-name']):print(i+1,'\n'.join(lines[max(0,i-4):i+9]))
for p in [Path('/mnt/e/edk2-samurai-out/kernel117/CamxChi/chi-cdk/api/sensor/camxmoduleconfig.xsd')]:
 if p.is_file(): print(p.read_text()[:15000])

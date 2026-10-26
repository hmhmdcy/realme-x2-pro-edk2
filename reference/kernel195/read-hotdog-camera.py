from pathlib import Path
import hashlib,json,subprocess
repo=Path('/home/cy122/x2pro-linux/hotdog-ref195');commit='47087509c4289c2580c54f5433e55366b2e00445';out=Path('/mnt/e/edk2-samurai-out/kernel195');dest=out/'hotdog-source-private';dest.mkdir(exist_ok=True)
files=['docs/camera-port-plan.md','docs/evidence/2026-08-10-mainline616-camera-imx471-popup.md','docs/evidence/2026-08-09-mainline616-camera-power-sequence.md']
prefix='aports/device/testing/linux-oneplus-hotdog-mainline616/'
files += [prefix+n for n in ['0102-media-add-OnePlus-hotdog-IMX471-front-camera.patch','0072-arm64-dts-hotdog-drop-invented-camera-rail-parents.patch','0083-media-i2c-sequence-hotdog-camera-rails.patch','0074-media-camss-program-the-sm8150-camnoc-qos.patch','0075-media-camss-vote-the-internal-sm8150-camnoc-path.patch','0076-media-camss-enable-the-sm8150-hf-axi-bridge.patch','0114-media-qcom-camss-unwind-failed-stream-starts.patch']]
records=[]
for name in files:
 data=subprocess.check_output(['git','show',commit+':'+name],cwd=repo);(dest/Path(name).name).write_bytes(data);records.append(dict(path=name,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
 lines=data.decode().splitlines();print('\nFILE',name)
 if name.endswith('.md'):print('\n'.join(lines[:140]))
 elif '0102-' in name:
  for i,line in enumerate(lines):
   if any(v in line for v in ['power_on(','power_off(','power-domains','regulator_bulk','regulator_enable','sleep_range','pm_runtime','native_width','supported_modes','power_seq']):print('\n'.join(lines[max(0,i-3):min(len(lines),i+9)]))
 else:print('\n'.join(lines[:85]))
(out/'hotdog-source-manifest-private.json').write_text(json.dumps(records,indent=2)+'\n')
ref=Path(__file__).resolve().parent;r=json.loads((ref/'hotdog-reference-validation.json').read_text());r.update(camera_source_files=records,no_foreign_gpio_regulator_or_popup_wiring_applied=True,no_foreign_scripts_executed=True);(ref/'hotdog-reference-validation.json').write_text(json.dumps(r,indent=2)+'\n')

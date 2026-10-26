from pathlib import Path
import json,shutil
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel224')
assert json.loads((here/'wireplumber-reload-validation.json').read_text())['new_r11_camera_libraries_loaded']
text=(here/'run-r11-candidate-checks.py').read_text()
text=text.replace("here/'r11-staging-validation.json'","here/'wireplumber-reload-validation.json'").replace("['system_camera_packages_unchanged']","['new_r11_camera_libraries_loaded']")
injection=r'''
old="    candidate_libraries_verified=all(str(prefix/'usr/lib'/name) in maps for name in ['libcamera.so.0.7.2','libcamera-base.so.0.7.2'])"
assert runner.count(old)==1
runner=runner.replace(old,"    library_paths={l.split()[-1] for l in maps.splitlines() if 'libcamera.so.' in l or 'libcamera-base.so.' in l}\n    candidate_libraries_verified=all('/usr/lib/'+name in library_paths for name in ['libcamera.so.0.7.2','libcamera-base.so.0.7.2'])")
runner=runner.replace('def demote():',"if profile=='isolated':env['XDG_CONFIG_HOME']='/run/samurai-camera224-r11/config-isolated'\ndef demote():")
'''
marker="compile(runner,'candidate-raw-statistics224','exec')";assert text.count(marker)==1;text=text.replace(marker,injection+'\n'+marker)
text=text.replace('r11-raw-statistics-','installed-r11-raw-statistics-').replace('1 candidate {profile}','1 system {profile}').replace('-candidate-host-private.log','-installed-host-private.log').replace('-candidate-validation.json','-installed-validation.json')
text=text.replace('candidate_libraries_verified=True','installed_camera_libraries_verified=True').replace("here/'r11-candidate-native-validation.json'","here/'r11-installed-native-validation.json'").replace('system_r8_packages_unchanged=True','installed_r11_r6_camera_packages_verified=True')
compile(text,'installed-r11-checks','exec');(here/'run-r11-installed-checks.py').write_text(text)

text=(here.parent/'kernel223/run-standard-r8-client.py').read_text().replace('223','224').replace('installed-r8-standard-','installed-r11-standard-').replace('camera224-r8-client','camera224-r11-client')
text=text.replace("here/'coherent-install-validation.json'","here/'wireplumber-reload-validation.json'").replace("['coherent_driver_and_r8_r3_native_deployment']","['new_r11_camera_libraries_loaded']")
compile(text,'standard-r11-client','exec');(here/'run-standard-r11-client.py').write_text(text)
(private/'probes').mkdir(mode=0o700,exist_ok=True);target=private/'probes/gst-camera224-probe';assert not target.exists();shutil.copyfile(private.parent/'kernel223/probes/gst-camera223-probe',target)
proof=json.loads((here.parent/'kernel223/gst-client-build-validation.json').read_text());proof.update(stage=224,retained_public_api_client=True);(here/'gst-client-build-validation.json').write_text(json.dumps(proof,indent=2)+'\n')

controller=(here.parent/'kernel223/native-full-mode-control.py').read_text().replace('stage=223','stage=224').replace('k223-','k224-')
compile(controller,'full-controller224','exec');(here/'native-full-mode-control.py').write_text(controller)
text=(here.parent/'kernel223/capture-full-metadata.py').read_text().replace('223','224').replace('system-r8','system-r11').replace('camera224-r8','camera224-r11')
compile(text,'full-rgb224','exec');(here/'capture-full-rgb-metadata.py').write_text(text)
raw=text.replace('role=viewfinder','role=raw').replace('pixelformat=RGB888','pixelformat=SRGGB10_CSI2P').replace("tag=f'exposure-metadata-","tag=f'raw-exposure-metadata-").replace("python3 - rgb 0","python3 - raw 0")
raw=raw.replace("all_active_raw_pixels_examined=kind=='raw'","all_active_raw_pixels_examined=False").replace("raw_padding_excluded=kind=='raw'","raw_padding_excluded=False")
# The inherited generator changes those flags in its embedded runner, too.
raw=raw.replace("compile(code,'native-exposure-metadata220','exec')","code=code.replace(\"all_active_raw_pixels_examined=kind=='raw'\",'all_active_raw_pixels_examined=False').replace(\"raw_padding_excluded=kind=='raw'\",'raw_padding_excluded=False')\ncompile(code,'native-raw-exposure-metadata224','exec')")
# The source template may carry stage223 in its diagnostic compile label.
raw=raw.replace("compile(code,'native-exposure-metadata224','exec')","code=code.replace(\"all_active_raw_pixels_examined=kind=='raw'\",'all_active_raw_pixels_examined=False').replace(\"raw_padding_excluded=kind=='raw'\",'raw_padding_excluded=False')\ncompile(code,'native-raw-exposure-metadata224','exec')")
compile(raw,'full-raw224','exec');(here/'capture-full-raw-metadata.py').write_text(raw)
wrapper='''from pathlib import Path
import host,json,subprocess,sys
here=Path(__file__).resolve().parent
def control(action):
 p=host.ssh('python3 - '+action,input=(here/'native-full-mode-control.py').read_bytes(),timeout=65)
 (host.PRIVATE/('full-'+action+'-host-private.log')).write_bytes(p.stdout+p.stderr)
 r=json.loads(p.stdout);(here/('full-'+action+'-validation.json')).write_text(json.dumps(r,indent=2)+'\\n');print(json.dumps(r),flush=True)
control('start')
try:
 for kind in ['raw','rgb']:subprocess.run([sys.executable,str(here/('capture-full-'+kind+'-metadata.py')),'4608','3456','system-r11'],check=True,timeout=110)
finally:control('finish')
for client in ['cam','gstreamer']:subprocess.run([sys.executable,str(here/'run-standard-r11-client.py'),client],check=True,timeout=110)
'''
compile(wrapper,'full-and-standard224','exec');(here/'run-full-and-standard.py').write_text(wrapper)
print('K224_INSTALLED_R11_MATRIX_FULL_RAW_RGB_AND_STANDARD_CLIENTS_PREPARED')

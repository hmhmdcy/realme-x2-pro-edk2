from pathlib import Path
import json

here=Path(__file__).resolve().parent
assert json.loads((here/'wireplumber-reload-validation.json').read_text())['new_r13_camera_libraries_loaded']
text=(here/'native-r13-manual-runner.py').read_text().replace("tag=f'manual-controls-r13-","tag=f'manual-controls-r13-system-")
old="candidate_libraries_verified=all(str(prefix/'usr/lib'/name) in maps for name in ['libcamera.so.0.7.2','libcamera-base.so.0.7.2'])"
new="actual_prefix=str(prefix/'usr/lib') if library=='candidate' else '/usr/lib'\n    library_maps='\\n'.join(l for l in maps.splitlines() if 'libcamera.so.' in l or 'libcamera-base.so.' in l)\n    candidate_libraries_verified=all(actual_prefix+'/'+name in library_maps for name in ['libcamera.so.0.7.2','libcamera-base.so.0.7.2']) and '(deleted)' not in library_maps"
assert text.count(old)==1;text=text.replace(old,new);(here/'native-system-manual-runner.py').write_text(text)
text=(here/'run-r13-manual-case.py').read_text()
text=text.replace("assert json.loads((here/'r13-staging-validation.json').read_text())['system_camera_packages_unchanged']","assert json.loads((here/'r13-package-install-validation.json').read_text())['transaction_state']=='verified'")
text=text.replace('native-r13-manual-runner.py','native-system-manual-runner.py').replace('1 candidate {profile}','1 system {profile}').replace('manual-controls-r13-','manual-controls-r13-system-').replace("label=f'r13-","label=f'r13-system-").replace('candidate_framework=','installed_framework=').replace('system_r11_r6_packages_unchanged=True','installed_r13_r8_payloads_verified=True')
(here/'run-installed-manual-case.py').write_text(text)
for p in ['native-system-manual-runner.py','run-installed-manual-case.py']:compile((here/p).read_text(),p,'exec')
print('Installed default-library checks prepared; candidate matrix evidence retained.')

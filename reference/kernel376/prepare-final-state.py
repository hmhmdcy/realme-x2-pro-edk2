from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel375/final-state.py').read_text()
s=s.replace("assert json.loads((HERE/'camera-runtime-validation.json').read_text())['passed']", "assert json.loads((HERE.parent/'kernel375/camera-runtime-validation.json').read_text())['passed']\nassert json.loads((HERE/'session-runtime-validation.json').read_text())['passed']")
s=s.replace("b'/var/lib/samurai/k375-'", "b'/var/lib/samurai/k375-',b'/var/lib/samurai/k376-'")
s=s.replace('stage=375','stage=376').replace('normal_camera_capture_passed=True','normal_camera_capture_reference_stage=375,camera_capture_repeated=False,same_boot_as_camera_reference=True')
s=s.replace('icp_image_sessions_tested=False','icp_sessions_created_destroyed=2,ipe_image_processing_verified=False')
(HERE/'final-state.py').write_text(s)
print('Prepared376 current health/resources validation; reuse375 same-boot unchanged camera capture evidence.')

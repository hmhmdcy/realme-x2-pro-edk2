from pathlib import Path
HERE=Path(__file__).resolve().parent
base=(HERE.parent/'kernel437/check-hardware.py').read_text()
# Keep the full GTM/TMC/PD10/history audit, with the two camera labels.
base=base.replace("else 'r2'","else 'r1'")
base=base.replace("source=(HERE.parent/'kernel435/check-hardware.py').read_text();", "source=(HERE.parent/'kernel435/check-hardware.py').read_text().replace(\"name=='scene-native'\",\"name.endswith('scene-native')\");")
base=base.replace('stage=437','stage=438').replace('main_awb_converged_and_continuous_metadata_verified=True','wide_tele_awb_converged_and_continuous_metadata_verified=True')
base=base.replace('other_cameras_auto_tone_not_yet_validated=True','front_full_ipe_colour_tone_pending=True')
base=base.replace("'hardware-validation.json'","'hardware-validation.json'")
exec(compile(base,str(HERE/'hardware-audit-adapter.py'),'exec'))

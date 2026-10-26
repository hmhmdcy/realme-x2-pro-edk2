from pathlib import Path
here=Path(__file__).resolve().parent
text=(here/'run-raw-dark-probe.py').read_text()
text=text.replace("sys.argv[3] in ['0','2']", "sys.argv[3]=='4'")
text=text.replace("tag=variant+'-'+kind+'-p'+str(pattern)","tag=variant+'-'+kind+'-csid-p'+str(pattern)+'-r2'")
text=text.replace("'raw-dark-probe-build-validation.json'", "'csid-known-input-probe-build-validation.json'").replace("['raw10_dark_statistics_probe_built']", "['csid_known_input_probe_built']")
text=text.replace("names=['exposure'", "csids=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='msm_csid0'];assert len(csids)==1;csid='/dev/'+csids[0].name\nassert subprocess.check_output(['v4l2-ctl','-d',csid,'--get-ctrl=test_pattern'],text=True).strip()=='test_pattern: 0'\nlink_expression='\"msm_csiphy2\":1 -> \"msm_csid0\":0 [1]'\n(out/'media-before-private.txt').write_bytes(subprocess.check_output(['media-ctl','-d','/dev/media0','-p']))\nnames=['exposure'")
text=text.replace("['/run/samurai-camera213-raw-dark-probe',node,kind,str(pattern)]", "['/run/samurai-camera213-csid-known-input-probe',csid,kind,str(pattern)]")
text=text.replace("finally:\n    for group", "finally:\n    subprocess.run(['v4l2-ctl','-d',csid,'--set-ctrl=test_pattern=0'],capture_output=True,check=True,timeout=10)\n    subprocess.run(['media-ctl','-d','/dev/media0','--links',link_expression],capture_output=True,check=True,timeout=10)\n    for group")
text=text.replace("assert controls()==saved", "assert controls()==saved\nassert subprocess.check_output(['v4l2-ctl','-d',csid,'--get-ctrl=test_pattern'],text=True).strip()=='test_pattern: 0'\n(out/'media-after-private.txt').write_bytes(subprocess.check_output(['media-ctl','-d','/dev/media0','-p']))")
text=text.replace("requested_sensor_pattern=pattern", "csid_all_ones_pattern=pattern,physical_sensor_input_detached_during_test=True,physical_input_link_restored=True,known_input_raw10_white=1023")
text=text.replace("test_pattern_effectiveness_not_assumed=True", "generator_effectiveness_requires_raw_confirmation=True")
text=text.replace("subprocess.check_output(['v4l2-ctl','-d',csid,'--get-ctrl=test_pattern'],text=True).strip()=='test_pattern: 0'", "re.search(r'^test_pattern:\\s*0(?:\\s|\\(|$)',subprocess.check_output(['v4l2-ctl','-d',csid,'--get-ctrl=test_pattern'],text=True))")
(here/'run-csid-known-input-probe.py').write_text(text)

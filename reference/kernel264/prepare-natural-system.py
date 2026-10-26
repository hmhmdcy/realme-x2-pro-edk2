"""Verify normal client release without changing media state behind libcamera's cache."""
from pathlib import Path
R=Path(__file__).parent
s=(R/'native-system.py').read_text().replace('range(6000070,6000075)','range(6000080,6000085)')
s=s.replace("system_services=json.loads((root/'k264-services/summary.json').read_text())['new_processes']", "system_services=json.loads((root/'k264-services-current-private.json').read_text())['new_processes']")
start=s.index(" for path,values in patterns.items():attempt('csid-pattern:")
end=s.index(' time.sleep(2)',start)
s=s[:start]+" # Production libcamera owns graph/formats/AE state. Observe its normal release.\n"+s[end:]
needle=" control_match=all(attempt('verify-controls:'+p,lambda p=p,v=v:get_controls(p,sorted(v)))==v for p,v in saved_controls.items())"
assert s.count(needle)==1
s=s.replace(needle,needle+"\n patterns_and_flips_zero=all(get_controls(p,['test_pattern'])['test_pattern']==0 for p in set(patterns)|set(saved_controls)) and all(not get_controls(p,[name])[name] for p,values in saved_controls.items() for name in ['horizontal_flip','vertical_flip'] if name in values)")
s=s.replace('all_formats_restored=','formats_match_before=').replace('media_graph_restored=','media_graph_matches_before=').replace('sensor_controls_restored=','sensor_controls_match_before=')
s=s.replace("  camera_devices_suspended=suspended,", "  cleanup_policy='normal_libcamera_release_without_external_media_writes',test_patterns_and_flips_zero=patterns_and_flips_zero,\n  camera_devices_suspended=suspended,")
s=s.replace("['all_formats_restored','media_graph_restored','sensor_controls_restored','rails_unchanged'", "['test_patterns_and_flips_zero','rails_unchanged'")
s=s.replace("delay==6000074", "delay==6000084").replace('delay!=6000074','delay!=6000084')
(R/'native-system-natural.py').write_text(s)
p=R/'system-runner.py';s=p.read_text().replace('assert mode in range(6000070,6000075)',"assert mode in list(range(6000070,6000075))+list(range(6000080,6000085))\nscenario=mode-10 if mode>=6000080 else mode")
for value in [6000070,6000071,6000072,6000073]:s=s.replace('if mode=='+str(value)+':','if scenario=='+str(value)+':')
p.write_text(s)
p=R/'run-system.py';s=p.read_text().replace('assert mode in range(6000070,6000075)', 'assert mode in list(range(6000070,6000075))+list(range(6000080,6000085))')
s=s.replace("snapshot=host.PRIVATE", "worker='native-system-natural.py' if mode>=6000080 else 'native-system.py'\nsnapshot=host.PRIVATE")
s=s.replace("'native-system.py']", "worker]").replace("if name=='native-system.py':continue", "if name==worker:continue").replace("(snapshot/'native-system.py').read_bytes()", "(snapshot/worker).read_bytes()")
p.write_text(s)
p=R/'run-system-suite.py';s=p.read_text().replace('range(6000070,6000075)','range(6000080,6000085)');(R/'run-system-natural-suite.py').write_text(s)

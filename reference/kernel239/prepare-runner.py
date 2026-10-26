from pathlib import Path
import ast
R=Path(__file__).resolve().parent
p=R/'native-fixed-rgb.py';text=p.read_text()
text=text.replace("save('controlled-48-frame-capture-trace-armed')", "save('fixed12-frame-rgb-debug-trace-armed')")
text=text.replace('explicit_exposure_gain_phases=True','fixed_exposure_gain=True')
old=" report['diagnostic_capture_completed']=bool(not error and process is not None and process.returncode==0 and len(frames)==12 and not timed and not killed and not restore_errors and report['taint']==0 and not any(faults.values()));"
new=" report['diagnostic_capture_completed']=bool(not error and process is not None and process.returncode==0 and len(frames)==12 and not timed and not killed and all(report[k] for k in ['all_formats_restored','media_graph_restored','sensor_controls_restored','rails_unchanged','camera_devices_suspended','mclk1_mclk2_disabled','cpu_rgb_control_metadata_verified','candidate_core_and_ipa_mapped','trace_instance_removed']) and not restore_errors and report['taint']==0 and not any(faults.values()));"
assert text.count(old)==1;text=text.replace(old,new)
assert "LIBCAMERA_LOG_LEVELS='*:INFO,SimplePipeline:DEBUG,Debayer:DEBUG,IPASoftBL:DEBUG'" in text
ast.parse(text);p.write_text(text)
print('239 runner distinguishes completed diagnostic from strict nonzero acceptance')

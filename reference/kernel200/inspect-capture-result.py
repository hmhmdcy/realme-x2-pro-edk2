from pathlib import Path
import json,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k200-runtime/boot-id-private.txt').read_bytes()
p=root/'k200-front-capture-r1/summary.json';r=json.loads(p.read_text())
result={k:r.get(k) for k in ['stage','normal_driver_bound','physical_id_accepted_by_normal_driver','physical_media_graph_present','physical_image_capture','capture_returncode','camss_original_graph_restored','pins_restored_exact','fault_delta','taint','attempts','persistent_candidate_rebound']}
result['capture_cycle_count']=len(r.get('capture_cycles',[]));result['physical_frame_count']=sum(len(x['frames']) for x in r.get('capture_cycles',[]))
result['diagnostic_modules_remaining']=[n for n in ['imx471','samurai_front_overlay','samurai_vio_phandle','samurai_cci_bringup','qcom_pm8008','qcom_pm8008_regulator','v4l2_cci','i2c_qcom_cci'] if Path('/sys/module/'+n).exists()]
print(json.dumps(result))

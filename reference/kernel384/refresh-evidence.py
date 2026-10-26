from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=json.loads(p.read_text());assert d['stage']==384
 d.update(icp_latest_device_experiment_stage=384,icp_latest_hfi_response_latency_ms=None,
  icp_sys_init_evidence=prefix+'reference/kernel384/boot-runtime-r1-validation.json',
  icp_full_hfi_lifecycle_evidence=prefix+'reference/kernel384/boot-runtime-validation.json',
  ipe_sessions_hardware_evidence=prefix+'reference/kernel384/boot-runtime-validation.json',
  ipe_config_io_hardware_evidence=prefix+'reference/kernel384/boot-runtime-validation.json',
  ipe_pixel_transfer_evidence=prefix+'reference/kernel384/pixels-validation.json',
  ipe_preboot_reset_ack_evidence=prefix+'reference/kernel384/boot-runtime-validation.json',
  ipe_failure_dma_retention_model_evidence=prefix+'reference/kernel384/transfer-validation.json')
 p.write_text(json.dumps(d,indent=2)+'\n')
print('Latest control/pixel/retention evidence references updated.')

from pathlib import Path
import hashlib,json,re
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
inputs=json.loads((P/'isp-source-inputs-private.json').read_text())
for name,proof in inputs.items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==proof['sha256']
oem=(P/'oem-cam_vfe170.h').read_text();ops=(P/'maintained-camss-vfe-17x.c').read_text();board=(P/'maintained-camss.c').read_text()
outputs=re.findall(r'\.vfe_out_type\s*=\s*(CAM_VFE_BUS_VER2_\w+)',oem);assert len(outputs)==18
assert all('CAM_VFE_BUS_VER2_VFE_OUT_'+s in outputs for s in ['RDI0','RDI1','RDI2','FULL','DS4','DS16','RAW_DUMP','FD'])
assert 'MODE_MIPI_RAW << WM_CFG_MODE' in ops and '/* Configure stride for RDIs */' in ops
assert '.num_client = 20' in oem and '.num_out = 18' in oem and 'vfe_res_8150[]' in board
out=dict(stage=274,sources=inputs,oem_vfe170_bus_clients=20,oem_vfe170_outputs=outputs,maintained_vfe170_writer_is_mipi_raw=True,
 processed_pixel_and_statistics_paths_not_connected=True,resource_formats_pix_name_does_not_prove_processing=True,
 current_runtime_uses_cpu_software_isp=True,no_spectra_registers_written_by_this_audit=True,no_new_isp_driver_implemented=True,
 required_layers=dict(soc='VFE170 CAMIF/PIX modules, output DMA and statistics, IRQ/reset/PM',board='Existing SM8150 clocks, domains, CSI routing and memory constraints; no image-processing policy',
  kernel_uapi='Reviewed V4L2 media/request/parameter/statistics interfaces rather than unrestricted register writes',userspace='Pipeline handler, matching IPA algorithms and per-module calibration/tuning'))
(R/'isp-gap-validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(stage=274,oem_outputs=len(outputs),sources=len(inputs),hardware_processing_still_unimplemented=True),indent=2))

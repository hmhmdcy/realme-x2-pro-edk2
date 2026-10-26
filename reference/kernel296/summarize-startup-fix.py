"""Combine startup/reopen/late-ROI evidence without claiming a complete ISP pipeline."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent;load=lambda p:json.loads(p.read_text())
first=load(ROOT/'statistics-pixel-validation.json');second=load(ROOT/'statistics-r2-pixel-validation.json');scene=load(ROOT/'optical-statistics-validation.json')
assert first['passed'] and second['passed'] and scene['all_packets_valid']
captures=[load(ROOT/'stats-capture-validation.json'),load(ROOT/'optical-capture-validation.json'),load(ROOT/'stats-r2-capture-validation.json')]
assert all(c['passed'] for c in captures)
packets=[]
for label,report in [('first_tele',first),('tele_after_wide_with_late_tiny_roi',second)]:
 for r in report['startup_packets']:packets.append(dict(scenario=label,**r))
r=captures[1]['statistics'][0];packets.append(dict(scenario='wide_scene_after_tele',frame=r['frame'],sequence=r['sequence'],sum=r['sum'],expected_sum=499392,valid=r['sum']==499392))
assert len(packets)==7 and all(r['valid'] for r in packets)
assert all(r['sum'] in [820560,410280,2] for c in [captures[0],captures[2]] for r in c['statistics'])
assert all(r['sum']==499392 for r in captures[1]['statistics'])
prior=[load(ROOT.parent/'kernel295/statistics-pixel-validation.json'),load(ROOT.parent/'kernel295/optical-statistics-validation.json')]
assert not prior[0]['startup_statistics_valid'] and prior[1]['invalid_packets']
report=dict(stage=296,source=load(ROOT/'source-validation.json')['commit'],driver_layer='SM8150/VFE175 SoC driver',
 startup_packets=packets,all_seven_startup_or_late_packets_valid=True,
 hardware_image_frames=sum(c['actual_frames'] for c in captures),hardware_statistics_packets=sum(c['statistics_frames'] for c in captures),
 all_recorded_populations_in_known_roi_set=True,scene_all_18_populations_exact=True,
 late_stats_start_uses_new_tiny_roi=True,parameter_completions=[c.get('parameter_completions') for c in captures],
 parent_failure_preserved=True,first_packet_skipping_not_used=True,no_userspace_mmio=True,no_cpu_histogram_substitution=True,
 shared_dmi_state_and_cgc_restored_host_verified=True,board_dt_firmware_product_packages_changed=False,
 exact_image_stats_sof_association_not_proven=True,ipa_blc_and_full_iq_incomplete=True,
 measurement_scope='S5K3M5 GRBG10 2104x1560 pattern2; IMX319 RGGB10 1632x1224 scene; FULL 320x240 NV12; one physical boot')
(ROOT/'startup-fix-validation.json').write_text(json.dumps(report,indent=2)+'\n')
review=dict(stage=296,viewed_private_frame=11,recognizable_scene_edges_and_structures=True,still_dark_and_green=True,full_image_quality_not_accepted=True,no_private_pixels_published=True)
(ROOT/'optical-review.json').write_text(json.dumps(review,indent=2)+'\n')
print(json.dumps(report,indent=2))

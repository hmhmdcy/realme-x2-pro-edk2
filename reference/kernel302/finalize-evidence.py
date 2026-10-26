"""Promote only the final mode-complete bundle's two verified executions."""
from pathlib import Path
import hashlib,json,re
import host
HERE=Path(__file__).resolve().parent;load=lambda n:json.loads((HERE/n).read_text())
bundle=load('ipa-bundle-r2-validation.json');build=load('build-validation.json');contract=load('ipa-contract-validation.json')
assert build['build_exit']==0 and build['attempt']==4 and contract['real_module_dlopen_contract_exit']==0
assert contract['module_sha256']==bundle['files']['ipa/ipa_camss_vfe.so']['sha256']
tree=Path(build['isolated_source'])
for name,digest in build['source_sha256'].items():assert hashlib.sha256((tree/name).read_bytes()).hexdigest()==digest
runs={}
for run in ['r3','r4']:
 cap=load(f'controls-capture-{run}-validation.json');assoc=load(f'control-association-{run}-validation.json')
 assert cap['passed'] and cap['sensor_metadata_frames']==cap['application_frames']==480
 assert assoc['archive_sha256']==bundle['archive_sha256'] and assoc['standard_manual_mode_metadata_frames']==480
 assert assoc['all8_phone_bundle_hashes_match'] and assoc['independent_request_source_sof_quantized_metadata_crosscheck']
 assert assoc['all_bhist_changes_align_with_effective_metadata'] and assoc['all_useful_output_bands_align_with_effective_metadata']
 assert assoc['delayed_control_write_sof_verified'] and assoc['all_logged_writes_effective_at_sof_plus2'] and assoc['useful_output_band_changes']==72
 log=(host.PRIVATE/f'controls-{run}-capture-private.log').read_text();assert len(re.findall(r'IPA init pid=\d+ model=imx319',log))==1
 poll=json.loads((host.PRIVATE/f'controls-{run}-poll-private.json').read_text());assert poll['state']['terminal'] and not poll['matching_worker_live'] and not poll['matching_child_live']
 runs[run]=dict(frames=480,standard_manual_mode_metadata_frames=480,source_changes=18,output_band_changes=72,all_logged_control_writes_effective_at_sof_plus2=True,
  forced_isolation=cap['ipa_isolation_forced'],request_to_effective_sof_offsets=assoc['request_to_effective_sof_offsets'],
  graph_and_resource_state_restored=cap['graph_restored'] and cap['before']==cap['after'],idle_restored_ms=cap['idle_observations'][-1]['elapsed_ms'])
assert runs['r3']['forced_isolation'] and not runs['r4']['forced_isolation']
out=dict(stage=302,actual_kernel_build=298,independent_crosscheck_passed=True,total_verified_application_frames=960,
 total_standard_manual_mode_metadata_frames=960,total_source_control_changes=36,total_useful_output_band_changes=144,
 archive_sha256=bundle['archive_sha256'],module_sha256=contract['module_sha256'],runs=runs,
 experimental_sensor_helper_and_delayed_controls_integrated=True,hardware_ae_or_awb_implemented=False,
 no_generic_helper_kernel_dt_firmware_or_product_package_changes=True,full_goal_complete=False)
(HERE/'runtime-association-validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))

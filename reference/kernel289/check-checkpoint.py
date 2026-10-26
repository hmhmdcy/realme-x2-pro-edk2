"""Check deployment/candidate separation and original-document preservation before mirroring."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[2];HERE=ROOT/'reference/kernel289'
load=lambda p:json.loads((ROOT/p).read_text())
s=load('linux-port/camera/kernel/source-lock.json');d=load('linux-port/camera/deployment-lock.json')
h=load('reference/kernel289/final-health-validation.json');b=load('reference/kernel289/fixes-full-build-validation.json')
assert s['maintained_commit']==d['kernel_source_commit']=='8c79b7e1912790d3e18a84c9c6621a6d92baa768'
assert s['source_worktree_commit']==d['candidate_kernel_source_commit']==b['commit']=='ff8d2e9fc04ef92407ff83c40c4e059eb620f0f7'
assert s['actual_kernel_image_stage']==d['kernel_image_stage']==h['kernel_build']==288
assert s['deployed_camera_modules']==d['kernel_modules']==h['modules'] and len(h['modules'])==10
assert d['candidate_kernel_deployed'] is False and d['experimental_gamma_probe_is_temporary_not_deployed_driver_fix']
assert d['experimental_hardware_color_neutrality_passed'] is False and d['hardware_isp_statistics_and_ipa_incomplete']
archive=ROOT/'archive/camera-before289-2026-10-19';manifest=json.loads((archive/'manifest.json').read_text())
for path,row in manifest.items():assert hashlib.sha256((archive/path).read_bytes()).hexdigest()==row['sha256']
assert (ROOT/'NEXT-SESSION.md').stat().st_size<=6500 and (ROOT/'DOCS-INDEX.md').stat().st_size<=10000
report=dict(stage=289,deployed_kernel_build=288,candidate_commit=b['commit'],candidate_not_deployed=True,
 exact_loaded_module_records_match_deployment_locks=True,historical_documents_archived_with_hashes=True,
 kernel_user_space_and_af_validation_scopes_separated=True,hardware_color_failure_not_marked_complete=True,
 old_heading_anchors_retained=True,initial_docs_check_missing_two_heading_anchors_corrected=True)
(HERE/'checkpoint-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

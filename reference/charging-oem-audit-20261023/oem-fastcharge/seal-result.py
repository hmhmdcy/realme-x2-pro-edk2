"""Seal the bounded offline recovery result without device access."""
from pathlib import Path
import hashlib,json,re,sys
HERE=Path(__file__).resolve().parent
PRIVATE=Path('E:/edk2-samurai-out/charging-management-20261023/oem-fastcharge-private') if sys.platform=='win32' else Path('/mnt/e/edk2-samurai-out/charging-management-20261023/oem-fastcharge-private')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
test=json.loads((HERE/'test-result.json').read_text());config=json.loads((HERE/'config-result.json').read_text())
manifest=json.loads((HERE/'source-manifest.json').read_text())
assert test['passed'] and test['gate_actual_function_cases']==10 and test['dispatch_predicate_differential_cases']==1024
assert test['conditional_array_actual_C_comparisons']==2 and len(test['rejection_boundaries'])==15
for name,digest in test['files'].items():assert sha(HERE/name)==digest
for entry in manifest['files']:assert sha(PRIVATE/'oem'/entry['path'].replace('/','--'))==entry['sha256']
for name,digest in test['private_generated'].items():assert sha(PRIVATE/'test-output'/name)==digest
files=['fastcharge_codec.py','extract-config.py','run-tests.py','fetch-fixed.py',
 'source-manifest.json','reference-source.json','config-result.json','test-result.json','README.md','seal-result.py','migrate-private.py','privacy-migration.json']
result=dict(passed=True,status='frozen offline parser/config recovery',repository=manifest['repository'],commit=manifest['commit'],
 files={n:sha(HERE/n) for n in files},source_files=manifest['files'],private_generated=test['private_generated'],existing_inputs=config['inputs'],
 recovered=dict(dt_node='oplus,stm8s-fastcg@26 / qupv3_se15_i2c',firmware_type='0x22',
  symbol='Stm8s_fw_data_4400_svooc_5000MA',selected_if_SM8150R=config['firmware_images']['True'],
  alternative_without_SM8150R=config['firmware_images']['False'],
  IC_selection_scope='fixed DT/software fallback, not physical silicon identification',
  branch_confirmation=config['branch_evidence'],
  ffc='vbatt_num=2 and no dual_ffc: OEM post-fastcharge transition directly FFC2; no high CV adopted'),
 next_gap='separate non-updating identity acquisition and exclusive handshake owner; current MCU/rail/version unknown',
 tests=dict(actual_gate_cases=10,source_predicate_differentials=1024,actual_C_array_comparisons=2,rejection_boundaries=15),
 MCU_firmware_written=False,standalone_firmware_binary_written=False,hardware_control_implemented=False,
 running_MCU_version_known=False,official_production_config_acquired=False,
 phone_accessed=False,ssh_executed=False,usb_accessed=False,sdk_invoked=False,shared_source_or_build_modified=False,
 old_suites_repeated=False,physical_fastcharge_validation=False,limits=['not a passive hardware listener','not an updater','no checksum/signature algorithm claim','not fastcharge permission','no icon or budget fix claim'])
(HERE/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(passed=True,result_sha256=sha(HERE/'result.json'),test_sha256=sha(HERE/'test-result.json'),codec_sha256=sha(HERE/'fastcharge_codec.py'))))

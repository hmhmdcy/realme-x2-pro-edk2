"""Reuse the unchanged ASAN-tested ownership predicate at the new RPC boundary."""
from pathlib import Path
import json
import storage
HERE=Path(__file__).resolve().parent;storage.mount.mounted_build()
tree=storage.candidate()/'src/libcamera-v0.7.2';baseline=tree.parents[1].parent/'libcamera442-bounded-dispatch/src/libcamera-v0.7.2'
name='src/libcamera/pipeline/camss-vfe/camss_vfe.cpp'
def predicate(text):
 a=text.index('    const uint64_t frameEpoch = epoch_;');z=text.index('    };',a)+7;return text[a:z]
text=(tree/name).read_text();assert predicate(text)==predicate((baseline/name).read_text())
prior=json.loads((HERE.parent/'kernel441/reentry-validation.json').read_text());assert prior['passed'] and prior['host_asan_ubsan']
finish=text[text.index('void CamssVfeData::finish('):text.index('void CamssVfeData::imageProcessed(')]
assert finish.count('if (!ownsFrame()) return;')==3
assert finish.index('ipa_->frameMetadata(')<finish.index('if (!ownsFrame()) return;')<finish.index('Image controls recovered')
a=finish.index('ipa_->prepareFocusedIpe(');b=finish.index('if (!ownsFrame()) return;',a)
assert a<finish.index('ipa_->processFocus(',a)<b<finish.index('if (!ret) request->_d()->metadata().merge(metadata);',b)
a=finish.index('else ret=ipa_->prepareIpeParameters(');b=finish.index('if (!ownsFrame()) return;',a)
assert a<b<finish.index('qcom_ipe_a5_frame_params packet{};',b)
r=dict(stage=444,actual_production_ownership_predicate_byte_identical_to442=True,
 retained441_host_asan_ubsan_proof_reused=True,combined_and_separate_focus_paths_share_guard_before_request_access=True,
 metadata_fallback_and_tone_fallback_guards_retained=True,actual_full_pipeline_reentry_requires_hardware_validation=True,
 phone_accessed=False,passed=True)
(HERE/'reentry-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))

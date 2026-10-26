"""Review collected476 originals locally. No target or transport operations."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import runpy
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
FROZEN = HERE.parent / 'kernel476'
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True,
                        help='Private collected transaction directory containing original logs/state/plan/witness')
    parser.add_argument('--output', type=Path, required=True, help='Private output contains scene measurements')
    args = parser.parse_args()
    root = args.root
    inputs = {name: root / name for name in ['control-capture-private.log', 'state.json',
              'control-live-witness-private.json', 'tele-plan-private.json']}
    data = {name: json.loads(path.read_text()) for name, path in inputs.items() if path.suffix == '.json'}
    state = data['state.json']
    plan = data['tele-plan-private.json']
    witness = data['control-live-witness-private.json']
    assert state['terminal'] and state['passed'] and state['phase'] == 'finished'
    assert state['failure'] is None and not state.get('cleanup_failure') and not state['new_faults']
    assert state['taint_after'] == state['taint_before'] == 0
    assert state['sensor_module_restored'] and state['formal_modules_restored'] and state['services_restored']
    assert state['tele_final_checks']['passed'] and state['tele_window_id'] == plan['window_id']
    assert plan['deployable'] and plan['kind'] == 'sensor-control-delay'
    assert plan['actual_sensor'] == [4208, 2368] and plan['expected_ll'] == 4848 and plan['expected_fll'] == 3312
    assert plan['no_ae'] and plan['no_delayed_controls'] and plan['delay_not_preset']
    expected = {
        'lib/libcamera.so.0.7.2': '9b352a12a8825935155106d17b81bb33ac60c4d14d7d2007efaad9e3f06af3af',
        'ipa/ipa_camss_vfe.so': '4c90047d42a91b9b1585d3b2cda997d8eee61f5e3a20f136b4345abcc2556d39',
        'proxy/camss_ipa_proxy': 'c7887708377b92b167d917173cb2840a78e437a773985fa087ef980bd382038c',
        'control-stepper-mode2-aarch64': 'd8b73c3b88f47716d4bc92e4e587f103d48c9d57bc317293f74befdd8455ce98',
        'delay-capture-mode2-aarch64': 'efaed465acb59ef653f28e7d2a2286dd511830759223f72acde5f686f751ef52',
        'mode2-measurement-private.yaml': 'c4ebe9473ebd068bca72280673b2579ce407bc9b9840f98c02aaf5a39f5b3ac8',
    }
    assert all(plan['common_payload'][name] == digest for name, digest in expected.items())
    assert witness['passed'] and witness['isolated'] and witness['old461_core_and_proxy']
    assert len(witness['processes']) == 3 and len({row['pid'] for row in witness['processes']}) == 3
    capture = state['control_capture']
    assert capture['steps'] == 9 and capture['exit_code'] == 0 and capture['ipe_jobs'] == 0
    assert capture['isolated'] and capture['live_witness'] and capture['no_delayed_controls'] and capture['no_ae_profile']
    frozen = json.loads((FROZEN / 'frozen-validation.json').read_text())
    analyser = FROZEN / 'analyse-local.py'
    assert sha(analyser) == frozen['files']['analyse-local.py']
    text = inputs['control-capture-private.log'].read_text(errors='replace')
    assert 'APPLICATION_RESULT result=0' in text and 'FIXTURE_RESTORATION result=0' in text
    result = runpy.run_path(str(analyser))['analyse'](text)
    assert result['all_application_frames_paired'] and result['application_frames'] == capture['frames']
    assert result['observed_sofs'] == 233
    assert len(re.findall(r'APPLICATION_FRAME number=\d+ request=\d+ sequence=\d+', text)) == capture['frames']
    assert not re.search(r'(?:IPE_PAIR |IPE_OBSERVE |AGC_APPLY|Automatic sensor update|SENSOR_WRITE)', text)
    result.update(review_stage=478, complete_transaction_verified=True,
                  original_inputs={name: sha(path) for name, path in inputs.items()},
                  frozen_analyser_sha256=sha(analyser),
                  per_write_readback='Executed and checked by472; not separately printed. Terminal stepper success required.',
                  no_delay_preset=True, target_accessed=False)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(passed=True, source_mode=2, application_frames=capture['frames'],
                         useful_steps=sum(row['useful_response'] for row in result['changes']),
                         no_delay_preset=True, output=str(args.output))))


if __name__ == '__main__':
    main()

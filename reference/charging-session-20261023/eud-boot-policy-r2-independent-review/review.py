"""Read-only, limited R2 review; no author tests or generators are executed."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[3]
author = root / 'reference/charging-oem-audit-20261023'
r1 = author / 'eud-boot-policy'
r2 = author / 'eud-boot-policy-r2'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
receipt_path = root / 'reference/charging-management-20261023/eud-csr-r8-result.json'
assert sha(receipt_path) == 'a8f5a8c5664220ea86bd74c85c6eabafe655c325ac696ae312075b0afed411b0'
assert sha(r2 / 'result.json') == '13c7d46205c1869d35a30060422222e0d2c991c1648274da94227f499cd9c77b'
old = r1.joinpath('PlatformBm.c.candidate').read_bytes()
new = r2.joinpath('PlatformBm.c.candidate').read_bytes()
before = (b'  // Do not mask away unknown bits or accept an unproven replicated word.\n'
          b'  return (Value == 0U) || (Value == 1U);')
after = (b'  // Match full words only; 0x01010101 was read twice on this board.\n'
         b'  return (Value == 0U) || (Value == 1U) || (Value == 0x01010101U);')
assert old.count(before) == new.count(after) == 1
assert old.replace(before, after) == new
assert b'MmioWrite32 (SAMURAI_EUD_CSR_ADDRESS, 0U);' in new
assert b'(Handoff->AfterCsr == 0U) ? EFI_SUCCESS : EFI_DEVICE_ERROR' in new
observation = json.loads(receipt_path.read_text())
assert observation['passed'] and observation['hardware_writes'] == 0
assert observation['csr_address'] == '0x088e1014' and observation['csr_width_bits'] == 32
assert [x['value'] for x in observation['csr']] == [0x01010101, 0x01010101]
assert observation['device_source_sha256'] == '810e220c03fab3f00fd88f2ddb742ee2c78ea5b7de09a84bf32997ef71bba6d8'
polls = [int(observation[k].split('polls=')[1].split()[0])
         for k in ['eud_rx_stats_before', 'eud_rx_stats_live', 'eud_rx_stats_after']]
assert polls[0] < polls[1] < polls[2]
for sample in observation['samples'] + [observation['post_sample']]:
    assert sample['valid'] == sample['online'] == sample['protection_ok'] == 1
    assert sample['desired_enable'] == 1 and sample['age_ms'] < 2000
    assert all(sample[k] == 0 for k in ['fault','error','stop_error','latched','cycle_timeout'])
result = {
    'status': 'no additional blocker in the two-line R2 change; not hardware acceptance',
    'candidate_sha256': sha(r2 / 'PlatformBm.c.candidate'),
    'delta_sha256': sha(r2 / 'r1-to-r2.patch'),
    'author_result_sha256': sha(r2 / 'result.json'),
    'observation_receipt_sha256': sha(receipt_path),
    'only_two_lines_changed_from_reviewed_R1': True,
    'exact_full_word_only_no_mask': True,
    'unknown_rejected_and_full_zero_target_readback_preserved': True,
    'R1_event_failure_panel_and_DTB_review_reused': True,
    'observation_rx_polls': polls,
    'new_author_tests_executed': False,
    'firmware_compiled': False,
    'device_accessed': False,
    'limits': ['Linux observation does not prove BeforeEBS hardware routing or CSR write success',
               'VOID callback cannot veto EBS after readback failure',
               'future build must bind actual cached inputs and prove baseline relink first'],
}
Path(__file__).with_name('review-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))

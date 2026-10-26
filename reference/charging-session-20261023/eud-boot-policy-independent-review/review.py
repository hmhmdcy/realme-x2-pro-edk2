"""Static read-only review of frozen boot-only policy; no author code run."""
from pathlib import Path
import difflib
import hashlib
import json
import re
import struct

HERE = Path(__file__).resolve().parent
AUTHOR = HERE.parents[1] / 'charging-oem-audit-20261023/eud-boot-policy'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(AUTHOR / 'result.json') == '27b0e6d83e38bfb4e9cfed370d5ce7289458b7e495035e56437991a8202912b3'
delivery = json.loads((AUTHOR / 'result.json').read_text())
assert all(sha(AUTHOR / name) == digest for name, digest in delivery['files'].items())
assert delivery['csr_accepts_full_words'] == [0, 1] and delivery['replica_accepted'] is False
base = (AUTHOR / 'PlatformBm.c').read_text()
candidate = (AUTHOR / 'PlatformBm.c.candidate').read_text()
fragment = (AUTHOR / 'eud-handoff-fragment.inc').read_text()
label = 'Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c'
patch = ''.join(difflib.unified_diff(base.splitlines(True), candidate.splitlines(True),
              fromfile='a/' + label, tofile='b/' + label))
assert patch.encode() == (AUTHOR / 'boot-policy.patch').read_bytes()


def function(text, name):
    pos = text.index('\n' + name + ' (')
    start = text.rfind('\nSTATIC\n', 0, pos) + 1
    return text[start:text.index('\n}', pos) + 2]


panels = ['SamuraiPanelBeforeExitBootServices', 'SamuraiArmPanelHandoff', 'SamuraiDisarmPanelHandoff']
assert all(function(base, n) == function(candidate, n) for n in panels)
panel_call = '''    Status = SamuraiArmPanelHandoff (&PanelHandoff);
    if (EFI_ERROR (Status)) {
      DEBUG ((DEBUG_WARN, "[SAMURAI] panel handoff unavailable: %r\\n", Status));
    }
    EfiBootManagerBoot (&NewOption);
    SamuraiDisarmPanelHandoff (&PanelHandoff);'''
assert panel_call in base and panel_call in candidate
cmd = lambda text: re.search(r'STATIC CHAR16\s+mSamuraiLinuxCmdLine\[\] =\s+L"([^"]+)";', text)[1]
removed = ['earlycon=eud,mmio,0x88e0000', 'console=eud']
assert cmd(candidate).split() == [t for t in cmd(base).split() if t not in removed]
load_block = lambda text: text[text.index('    CmdLineSize = '):text.index('    FreePool (DevicePath);')]
assert load_block(base) == load_block(candidate)
callback = function(candidate, 'SamuraiEudBeforeExitBootServices')
arm = function(candidate, 'SamuraiArmEudOffHandoff')
disarm = function(candidate, 'SamuraiDisarmEudOffHandoff')
assert 'STATIC SAMURAI_EUD_OFF_HANDOFF  mSamuraiEudOffHandoff;' in fragment
assert 'return (Value == 0U) || (Value == 1U);' in fragment
assert '0x088E1014U' in fragment and fragment.count('MmioWrite32 (') == 1
assert 'MmioWrite32 (SAMURAI_EUD_CSR_ADDRESS, 0U);' in callback
assert callback.index('Handoff->Attempted = TRUE;') < callback.index('MmioRead32 (')
assert 'Handoff->Cancelled || Handoff->Attempted' in callback
assert '(Handoff->AfterCsr == 0U) ? EFI_SUCCESS : EFI_DEVICE_ERROR' in callback
assert '&gEfiEventBeforeExitBootServicesGuid' in arm and 'TPL_CALLBACK' in arm
assert disarm.index('Handoff->Cancelled = TRUE;') < disarm.index('gBS->CloseEvent (')
assert 'if (EFI_ERROR (Handoff->CloseStatus)) {\n        return;' in disarm
assert candidate.index('goto SamuraiKernelBootDone;') < candidate.index(panel_call)
fifo = (AUTHOR / 'direct-fifo.inc').read_text()
assert fifo.index('if (mSamuraiEudOffHandoff.Attempted)') < fifo.index('MmioWrite32 (')

# Read the actual scheduling sources, not a model of UEFI callback ordering.
core = (AUTHOR / 'evidence--DxeMain.c').read_text()
tpl = (AUTHOR / 'evidence--Tpl.c').read_text()
event = (AUTHOR / 'evidence--Event.c').read_text()
start = core.index('\nCoreExitBootServices (')
core = core[start:core.index('\n}', start)]
ordered = ['CoreNotifySignalList (&gEfiEventBeforeExitBootServicesGuid)',
           'gTimer->SetTimerPeriod (gTimer, 0)', 'CoreTerminateMemoryMap (MapKey)',
           'CoreNotifySignalList (&gEfiEventExitBootServicesGuid)']
assert [core.index(t) for t in ordered] == sorted(core.index(t) for t in ordered)
assert 'if (PendingTpl <= NewTpl) {\n      break;' in tpl
assert 'Event->NotifyFunction (Event, Event->NotifyContext);' in event
drain = (AUTHOR / 'EudLogDxe.c').read_text()
serial = (AUTHOR / 'EudSerialPortLib.c').read_text()
assert '(MmioRead32 (EUD_BASE + EUD_REG_CSR_EUD_EN) & 0xFFU) != 1U' in drain
assert not re.search(r'MmioWrite32\s*\([^;]*CSR_EUD_EN', drain)
assert not re.search(r'Mmio(?:Write|Read)|MicroSecondDelay', serial.split('#include', 1)[1])
dsc = (AUTHOR / 'evidence--samurai.dsc').read_text()
assert '-DSAMURAI_ENABLE_EUD -DSAMURAI_LINUX_KERNEL' in dsc
assert 'SerialPortLib|Platform/Realme/sm8150/Library/EudSerialPortLib/EudSerialPortLib.inf' in dsc
early = (AUTHOR / 'drivers--tty--serial--eud_earlycon.c').read_text()
assert 'EARLYCON_DECLARE(eud, eud_setup)' in early and 'OF_EARLYCON_DECLARE' not in early
config = HERE.parents[1] / 'charging-oem-audit-20261023/apsd-integration/current-r7/snapshots/build--.config'
config_raw = config.read_text()
assert '\nCONFIG_CMDLINE=""\n' in config_raw
assert not re.search(r'^CONFIG_CMDLINE_(?:FORCE|EXTEND)=y$', config_raw, re.M)


def fdt(raw):
    h = struct.unpack_from('>10I', raw)
    magic, size, off_struct, off_strings, off_resv, version, last, bootcpu, string_size, struct_size = h
    assert magic == 0xd00dfeed and size == len(raw)
    strings = raw[off_strings:off_strings + string_size]
    p = off_struct; end = off_struct + struct_size; stack = []; nodes = set(); props = {}
    while p < end:
        token, = struct.unpack_from('>I', raw, p); p += 4
        if token == 1:
            stop = raw.index(b'\0', p); stack.append(raw[p:stop].decode('ascii'))
            nodes.add('/' + '/'.join(s for s in stack if s)); p = (stop + 4) & ~3
        elif token == 2:
            assert stack; stack.pop()
        elif token == 3:
            length, nameoff = struct.unpack_from('>2I', raw, p); p += 8
            name = strings[nameoff:strings.index(b'\0', nameoff)].decode('ascii')
            key = ('/' + '/'.join(s for s in stack if s), name)
            assert key not in props and p + length <= end
            props[key] = raw[p:p + length]; p = (p + length + 3) & ~3
        elif token == 4: pass
        elif token == 9:
            assert not stack; break
        else: raise AssertionError('unexpected FDT token')
    r = off_resv
    while struct.unpack_from('>2Q', raw, r) != (0, 0): r += 16
    return props, nodes, raw[off_resv:r + 16], (version, last, bootcpu)


native_base = Path('E:/edk2-samurai-out/charging-management-20261023/usb-boot/samurai-charging-private.dtb')
native_candidate = Path('E:/edk2-samurai-out/charging-management-20261023/eud-boot-policy-private/samurai-eud-off-policy-private.dtb')
assert sha(native_base) == delivery['native_base_sha256']
assert sha(native_candidate) == delivery['native_candidate_sha256']
before, bn, br, bh = fdt(native_base.read_bytes())
after, an, ar, ah = fdt(native_candidate.read_bytes())
assert bn == an and br == ar and bh == ah and before.keys() == after.keys()
changed = [k for k in before if before[k] != after[k]]
assert set(changed) == {('/soc@0/serial@88e0000', 'status'), ('/chosen', 'bootargs')}
assert after[('/soc@0/serial@88e0000', 'status')] == b'disabled\0'
old_args = before[('/chosen', 'bootargs')].rstrip(b'\0').decode().split()
new_args = after[('/chosen', 'bootargs')].rstrip(b'\0').decode().split()
assert new_args == [t for t in old_args if t not in removed] == cmd(candidate).split()
eud_nodes = {path for (path, name), raw in after.items() if name == 'compatible'
             and any(b'eud' in c for c in raw.split(b'\0'))}
assert eud_nodes == {'/soc@0/serial@88e0000'}
result = {'status': 'no-additional-blocker-in-static-candidate-scope',
          'author_result_sha256': sha(AUTHOR / 'result.json'),
          'candidate_sha256': sha(AUTHOR / 'PlatformBm.c.candidate'),
          'patch_sha256': sha(AUTHOR / 'boot-policy.patch'),
          'author_12_case_receipt_sha256': sha(AUTHOR / 'test-result.json'),
          'tests_reused_not_rerun': True,
          'panel_functions_and_original_call_block_unchanged': True,
          'utf16_load_options_unchanged_except_two_eud_tokens': True,
          'native_dtb_semantic_changes': [list(k) for k in changed],
          'native_candidate_sha256': sha(native_candidate),
          'all_other_dtb_values_nodes_reserved_map_preserved': True,
          'static_context_cancel_close_failure_and_single_attempt_verified': True,
          'arm_failure_refuses_current_kernel_boot': True,
          'before_ebs_precedes_mapkey_check_and_same_tpl_is_not_reentrant': True,
          'csr_address_width': '0x088e1014 / 32-bit', 'csr_accepts_full_words': [0, 1],
          'write_failure_does_not_prove_all_producers_quiet_or_stop_linux_boot': True,
          'old_carrier_source_linkage_limit': 'PlatformBm/INF only; bind all remaining frozen sources in future real build',
          'builtin_cmdline_empty_and_no_default_earlycon_or_enabled_com': True,
          'hardware_csr_zero_route_usb_or_budget_proven': False,
          'firmware_build_or_author_code_executed': False,
          'phone_ssh_usb_sdk_or_shared_write': False}
(HERE / 'review-result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
print(json.dumps(result, indent=2))

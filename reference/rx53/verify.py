#!/usr/bin/env python3
"""Verify the RX53 improvement and the independently confirmed remaining TX loss."""
from hashlib import sha256
import gzip
import json
from pathlib import Path
import re
import runpy

BASE=Path(__file__).resolve().parent
listed={}
for line in (BASE/'SHA256SUMS').read_text().splitlines():
    want,name=line.split('  ',1)
    assert name not in listed and sha256((BASE/name).read_bytes()).hexdigest()==want,name
    listed[name]=want
assert set(listed)=={p.name for p in BASE.iterdir() if p.is_file() and p.name!='SHA256SUMS'}
rows=json.loads((BASE/'exports.json').read_text()); assert len(rows)==62
for row in rows:
    data=(BASE/row['name']).read_bytes(); got=sha256(data).hexdigest()
    assert got==row['exported_sha256']
    if row['name'].endswith('.gz'):
        assert sha256(gzip.decompress(data)).hexdigest()==row['original_sha256']
    elif Path(row['name']).suffix in ('.raw','.bin','.py','.ps1','.cs','.c','.sh'):
        assert row['byte_identical'] and got==row['original_sha256']
    else:
        assert not data.startswith(b'\xef\xbb\xbf') and b'\r\n' not in data
usb,blob=runpy.run_path(str(BASE/'analyze-usb-success.py'))['analyze'](BASE)
assert usb==json.loads((BASE/'usb-success-summary.json').read_text()) and blob==(BASE/'usb-tx-journal.bin').read_bytes()
assert usb['partial_cancels']==[dict(status=-2,bytes=6,hex='90 04 5b 20 20 31')]
windows,blob=runpy.run_path(str(BASE/'analyze-windows-success.py'))['analyze'](BASE,BASE.parent/'rx51/analyze.py')
assert windows==json.loads((BASE/'windows-success-summary.json').read_text()) and blob==(BASE/'windows-tx-journal.bin').read_bytes()
loss,blob=runpy.run_path(str(BASE/'analyze-final-tx-loss.py'))['analyze'](BASE)
assert loss==json.loads((BASE/'final-tx-loss-summary.json').read_text()) and blob==(BASE/'final-tx-journal.bin').read_bytes()
assert loss['missing_seq']==7287 and loss['missing_wire']=='90 04 5b 20 20 20'
assert (loss['before_owner_matched'],loss['affected_owner_matched'],loss['recovery_owner_matched'])==(151,87,273)
assert loss['direct_matches']==511 and loss['command_and_receipts_complete']
epoch=json.loads((BASE/'source-epoch.json').read_text())
previous=json.loads((BASE.parent/'rx52/source-epoch.json').read_text())
driver=sha256((BASE/'eud-console-rx-candidate.c').read_bytes()).hexdigest()
assert driver==epoch['sha256']['driver']=='39e464f85b0450a394342b1664a306b2b27caa466b459ef038de2e0ccf6d2ef4'
assert epoch['sha256']['Image']=='33efc6bc0c1c2d7b82b80b39dc7cea2331d05cca2005376399dade92b1597952'
assert epoch['Image_bytes']==30181888 and epoch['kernel_revision']==previous['kernel_revision']
for name in ('DTB','config','init','busybox'): assert epoch['sha256'][name]==previous['sha256'][name]
old=(BASE.parent/'rx48/eud-journal-candidate.c').read_text(); new=(BASE/'eud-console-rx-candidate.c').read_text()
def function(source,name):
    start=re.search(r'^static .*?\b'+name+r'\([^;]*?\n\{',source,re.M).start()
    return source[start:source.index('\n}',start)+2]
for name in ('eud_send_frame','eud_probe','eud_reboot_cmd'): assert function(old,name)==function(new,name)
collector=function(new,'eud_rx_collect_locked')
assert collector.index('if (id == EUD_RX_UART_ID && len == 2)')<collector.index('for (i = 0; i < len; i++)')
assert not any(s in collector for s in ('pr_info(', 'tty_insert', 'kernel_restart('))
service=function(new,'eud_console_rx_locked'); assert service.index('!up->rx_irq_started')<service.index('readl(')
assert 'EUD_RX_SOURCE_CONSOLE' in service and 'rx_console_irq_credit = true' in service
assert 'else if (++up->rx_irq_empty_streak >= EUD_RX_IRQ_EMPTY_MAX)' in new
assert not re.search(r'warning:|error:',(BASE/'build-console-rx.log').read_text())
assert 'OBJCOPY arch/arm64/boot/Image' in (BASE/'build-console-rx.log').read_text()
for name,word in [('installed-native','R53NATIVE'),('installed-compatible','R53COMPAT'),('installed-final-native','R53END1')]:
    text=(BASE/(name+'.txt')).read_text(); assert '\n'+word+'\n' in text
    events=(BASE/(name+'.events.txt')).read_text(); assert 'attempt=2' not in events
assert 'sent=1 receipt=True' in (BASE/'console-rx-f1.events.txt').read_text()
assert 'F1 via=irq' in (BASE/'console-rx-f1.txt').read_text() and 'reboot2 bootloader requested' in (BASE/'console-rx-f1.txt').read_text()
assert 'product: msmnile' in (BASE/'candidate-f1-fastboot.txt').read_text()
boot=(BASE/'candidate-final-boot.txt').read_text()
assert 'TOP_CFG=00000011 original=00000000' in boot and 'shell started on /dev/ttyEUD0' in boot
assert 'IRQ armed virq=19 active=1 mask=01' in boot
state=json.loads((BASE/'final-state.json').read_text())
assert state['serial_closed'] and state['usb_owner_closed_and_detached'] and not state['known_eud_helpers']
assert state['flashed_partitions']==['logdump'] and state['flash_count']==1 and state['candidate_boots']==2
assert not state['new_windows_admin_capture'] and not state['installed_terminal_modified']
assert state['ports']==['COM14'] and len(state['devices'])==3 and all(d['Status']=='OK' for d in state['devices'])
assert not any('Attached' in s for s in state['target_usbipd'])
hashes={r['Path']:r['Hash'].lower() for r in state['hashes']}
assert hashes['E:\\RealmeX2Pro edk2\\linux-port\\eud.c']==driver
assert hashes['E:\\eud-host\\eud-terminal.ps1']==hashes['E:\\RealmeX2Pro edk2\\linux-port\\scripts\\eud-terminal.ps1']=='9c7a16f1f389a0dbbf3436f1383221cdf6c00e348f25b6e3590a479dab103d57'
assert hashes['E:\\edk2-samurai-out\\logdump-rx53-console-rx.img']=='50f951a4093dab3e4b93339a998b06583a01b75cd3c8cb39f67ca70e84fc5a93'
assert hashes['E:\\edk2-samurai-out\\logdump-rx48-tx-journal.img']=='61c0315cd24e24ce2bd020a8179647862eeacced28b142f21ffa0d2de00b953d'
print('RX53 verified: busy-console RX succeeds on USB and Windows; TX snapshot matches twice; one final issued prefix remains lost; goal unresolved.')

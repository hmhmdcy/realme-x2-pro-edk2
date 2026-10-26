"""Bind the existing handoff/source evidence before producing a review patch."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
REPO=Path('/home/cy122/edk2-samurai/repo')
REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
extra=['Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBootManagerLib.inf',
 'Platform/Realme/sm8150/samurai.dsc','Platform/Realme/sm8150/samurai.fdf.inc',
 'Platform/Realme/sm8150/EudLogDxe/EudLogDxe.inf',
 'Common/edk2/MdeModulePkg/Core/Dxe/DxeMain/DxeMain.c',
 'Common/edk2/MdeModulePkg/Core/Dxe/Event/Event.c','Common/edk2/MdeModulePkg/Core/Dxe/Event/Tpl.c']
sources={}
for name in extra:
 p=REPO/name;target=HERE/('evidence--'+p.name);target.write_bytes(p.read_bytes())
 sources[name]=dict(sha256=sha(p),bytes=p.stat().st_size,snapshot=target.name)
profile=(HERE/'evidence--samurai.dsc').read_text()
assert '-DSAMURAI_ENABLE_EUD' in profile and '-DSAMURAI_LINUX_KERNEL' in profile
assert 'SerialPortLib|Platform/Realme/sm8150/Library/EudSerialPortLib/EudSerialPortLib.inf' in profile
proof=json.loads((REF/'kernel164/source-validation.json').read_text())
linked={}
for name,digest in proof['after_sha256'].items():
 p=REPO/name;assert sha(p)==digest
 linked[name]=digest
build=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/usb-boot/generated-boot-builder-private.py')
b=build.read_text();assert "kernel164/source-validation.json" in b and b.count("source['after_sha256'].items()") ==2
carrier=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/usb-boot/boot-charging-usb-dt.img')
receipt=json.loads((REF/'charging-management-20261023/usb-boot-result.json').read_text())
assert sha(carrier)==receipt['boot_sha256']=='a30fb4440726e1c3ab80ad65277db4e57fec9a0924380cc07830a5c6e69ec280'
config=HERE.parent/'apsd-integration/current-r7/snapshots/build--.config'
text=config.read_text();assert 'CONFIG_CMDLINE=""' in text and 'CONFIG_CMDLINE_FORCE=y' not in text and 'CONFIG_CMDLINE_EXTEND=y' not in text
r=dict(passed=True,design='design-v1-frozen-before-patch',sources=sources,
 input_inspection_sha256=sha(HERE/'inspection.json'),
 carrier=dict(path=str(carrier),sha256=sha(carrier),build_receipt_sha256=sha(REF/'charging-management-20261023/usb-boot-result.json'),
  executed_builder_sha256=sha(build),source_guard_receipt_sha256=sha(REF/'kernel164/source-validation.json'),
  guarded_source_sha256=linked,
  limit='PlatformBm/INF source hashes were checked by the retained builder before/after build. Current EudLog/SerialPort/Core/DSC snapshots are not independently proven linked inputs to this old carrier; future build must bind frozen sources.'),
 config=dict(path=str(config),sha256=sha(config),builtin_cmdline='',force_enabled=False,extend_enabled=False),
 event_order=['BeforeExitBootServices notifications','stop global timer','validate MapKey','ordinary ExitBootServices notifications','clear boot services'],
 tpl='EUD handoff and EudLog timer both TPL_CALLBACK; CoreRestoreTpl does not dispatch equal-priority events into an executing callback',
 mmio=dict(address='0x088e1014',width_bits=32,known_full_word_values=[0,1,0x01010101],target=0,
  basis='Existing BDS writes/readback and the active EudLog timer use this exact address before the BeforeEBS phase; low byte is replicated on this board. No AHB2PHY/PHY/clock/role/secure registers are written by candidate.',
  limit='No electrical supply measurement or SoC bus-fault containment. Firmware-stage register access basis does not certify post-EBS PHY or direct USB operation.'),
 planned_changes=['independent static-context BeforeEBS callback and close lifecycle','arm failure refuses current kernel launch',
  'one callback attempt even when EBS MapKey fails/retries; zero write for already-zero/unknown',
  'direct BDS FIFO producer suppressed after attempt; existing timer skips on verified CSR0',
  'remove only eud earlycon/console tokens from UTF16 LoadOptions and native chosen bootargs','native COM status disabled'],
 panel_functions='all original panel functions and their call block must remain byte identical',
 no_new_kernel_or_runtime_API=True,no_firmware_build=True,phone_accessed=False,ssh_executed=False,sdk_invoked=False,shared_tree_modified=False)
(HERE/'design-evidence.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(passed=True,design_sha256=sha(HERE/'design-evidence.json'),carrier_sha256=sha(carrier))))

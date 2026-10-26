"""Read cached board/gauge/config sources only; no patch, build or device IO."""
from pathlib import Path
import gzip,hashlib,importlib.util,json,re,sys
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('gauge_status_storage284',REF/'kernel284/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
shared=storage.mounted_build();root=shared.parent/'source354'
files={n:root/n for n in ['drivers/power/supply/bq27xxx_battery.c','drivers/power/supply/bq27xxx_battery_i2c.c',
 'include/linux/power/bq27xxx_battery.h','Documentation/ABI/testing/sysfs-class-power']}
assert sha(files['drivers/power/supply/bq27xxx_battery.c'])=='b2cd415a995cb196559c0e4981988f737c17c98486449659d168314926aec69e'
ranges={'drivers/power/supply/bq27xxx_battery.c':[(483,523),(1049,1058),(1845,1958),(2121,2150),(2219,2227)],
 'drivers/power/supply/bq27xxx_battery_i2c.c':[(28,62),(178,190),(250,258),(289,297)],
 'Documentation/ABI/testing/sysfs-class-power':[(41,63),(79,96)]}
excerpts=[]
for name,spans in ranges.items():
 lines=files[name].read_text().splitlines();excerpts.append(name)
 for a,b in spans:excerpts.extend(f'{i+1}: {lines[i]}' for i in range(a-1,b))
(HERE/'kernel-excerpts.txt').write_text('\n'.join(excerpts)+'\n')
image=Path('/mnt/e/edk2-samurai-out/kernel363/Image-k363-private')
assert sha(image)=='15746aab311eed32478cdee4e13c1677716ff48c8a04316c9c15cf606c9d6468'
raw=image.read_bytes();configs=[]
for match in re.finditer(b'IKCFG_ST\x1f\x8b\x08',raw):
 start=match.start()+8;end=raw.find(b'IKCFG_ED',start)
 if end>start:
  try:configs.append(gzip.decompress(raw[start:end]).decode())
  except Exception:pass
assert len(configs)==1,'Require actual embedded Image config, not current shared config'
cfg=configs[0];selected=[x for x in cfg.splitlines() if 'BQ27' in x or x.startswith('CONFIG_IKCONFIG')]
assert 'CONFIG_BATTERY_BQ27XXX=y' in selected and 'CONFIG_BATTERY_BQ27XXX_I2C=y' in selected
dtb=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/usb-boot/samurai-charging-private.dtb')
assert sha(dtb)=='c559d2c4c9a83e85473b1b24724bb8938f1084bd3efcae9c4b67f37c2a4c4503'
# Reuse already-decompiled exact DTB; do not run any boot/firmware tool.
dts=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/eud-boot-policy-private/current-native.dts')
text=dts.read_text();node=re.search(r'fuel-gauge@55 \{.*?\n\s*\};',text,re.S).group()
assert 'compatible = "ti,bq28z610";' in node
(HERE/'board-config-excerpts.txt').write_text('Embedded exact Image363 IKCONFIG:\n'+'\n'.join(selected)+'\n\nExact cached native DTB decompile:\n'+node+'\n')
oemc=Path('/mnt/e/edk2-samurai-out/kernel83/realme-kernel-opensource--realmeX2pro-X3-AndroidR-kernel-source--drivers--power--oppo--gauge_ic--oplus_bq27541.c')
oemh=Path('/mnt/e/edk2-samurai-out/kernel85/official-oplus_bq27541.h')
ti=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/ti-manual-private.txt')
source_files=[*files.values(),image,dtb,dts,oemc,oemh,ti,REF/'charging-session-20261023/thermal-bands-candidate/samurai-mp2650.c',
 REF/'charging-ui-audit-20261023/upower-up-device-supply-battery.c',REF/'charging-oem-audit-20261023/icon-semantics/test-result.json']
result=dict(passed=True,scope='source/lock/board feasibility only; no executable patch or tests',
 files=[dict(path=str(p),sha256=sha(p)) for p in source_files],exact_Image_embedded_config_sha256=hashlib.sha256(cfg.encode()).hexdigest(),
 exact_Image_selected_config=selected,native_DT_gauge_compatible='ti,bq28z610',native_DT_gauge_address='0x55',
 built_in=True,hot_module_replacement_possible=False,precise_2719_silicon_identified=False,
 code_patched=False,compiled=False,phone_accessed=False,ssh_executed=False,USB_accessed=False,SDK_invoked=False,Git_invoked=False)
(HERE/'source-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(passed=True,embedded_config=selected,source_result_sha256=sha(HERE/'source-result.json')),indent=2))

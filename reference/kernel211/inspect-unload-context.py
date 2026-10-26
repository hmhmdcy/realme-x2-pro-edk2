from pathlib import Path
import json,re,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k211-before-reboot/boot-id-private.txt').read_bytes()
text=(root/'k211-quiesce/camera-unload-dmesg-private.txt').read_text();lines=text.splitlines();i=next(i for i,l in enumerate(lines) if 'WARNING:' in l)
messages=[l for l in lines[max(0,i-10):i+8] if "cam_cc_mclk2_clk status" in l or 'WARNING:' in l]
pd=Path('/sys/kernel/debug/pm_genpd/pm_genpd_summary').read_text();clocks=Path('/sys/kernel/debug/clk/clk_summary').read_text()
out=root/'k211-warning-context';out.mkdir(mode=0o700);(out/'genpd-private.txt').write_text(pd);(out/'clocks-private.txt').write_text(clocks)
print(json.dumps(dict(stage=211,warning_context=messages,current_camera_clocks=[l.strip() for l in clocks.splitlines() if 'cam_cc_mclk2_clk ' in l],taint=Path('/proc/sys/kernel/tainted').read_text().strip(),reboot_marker_exists=Path('/run/k211-bootloader-state').exists())))

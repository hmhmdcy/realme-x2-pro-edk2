from pathlib import Path
import json,os,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k198-trace-inspect';out.mkdir(mode=0o700);assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k198-baseline/boot-id-private.txt').read_bytes();t=Path('/sys/kernel/tracing');r=dict(stage=198,instances_supported=(t/'instances').exists(),root_tracing_on=(t/'tracing_on').read_text().strip(),root_set_event=(t/'set_event').read_text().splitlines(),events={})
for name in ['regmap/regmap_reg_write','regmap/regmap_reg_read','clk/clk_enable','clk/clk_disable','clk/clk_set_rate','power/runtime_pm_status']:
 p=t/'events'/name
 if p.exists():r['events'][name]=(p/'format').read_text()
(out/'formats.json').write_text(json.dumps(r,indent=2)+'\n');(out/'clocks-private.txt').write_bytes(Path('/sys/kernel/debug/clk/clk_summary').read_bytes());print(json.dumps(r))

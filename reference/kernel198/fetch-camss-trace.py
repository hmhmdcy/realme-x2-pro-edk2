from pathlib import Path
import host,json,re
out=host.PRIVATE;remote='/var/lib/samurai/k198-camss-trace/'
for n in ['regmap-clock-trace-private.txt','summary.json']:host.download(remote+n,out/n)
rows=(out/'regmap-clock-trace-private.txt').read_text().splitlines();regs=[];clock=[]
for line in rows:
 if 'tracing_mark_write:' in line or re.search(r'reg=(?:c1c8|c1bc|a004|c164)\b',line):regs.append(line)
 if re.search(r'clk_(?:enable|disable|set_rate): .*?(?:core_ahb|cpas_ahb|ife_0|slow_ahb)',line):clock.append(line)
print('trace_lines',len(rows));print('\n'.join(regs));print('relevant_clocks');print('\n'.join(clock));print('header','\n'.join(rows[:7]))

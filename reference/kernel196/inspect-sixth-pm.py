from pathlib import Path
import host,json
for n in ['summary.json','genpd-active-private.txt','clocks-active-private.txt','probe-trace-private.txt']:
 try:host.download('/var/lib/samurai/k196-front-probe-r6/'+n,host.PRIVATE/('front-r6-'+n))
 except Exception:
  if n=='probe-trace-private.txt':continue
  raise
r=json.loads((host.PRIVATE/'front-r6-summary.json').read_text());genpd=(host.PRIVATE/'front-r6-genpd-active-private.txt').read_text().splitlines();clocks=(host.PRIVATE/'front-r6-clocks-active-private.txt').read_text().splitlines();print(json.dumps(dict(driver_bound=r.get('normal_driver_bound'),runtime_cycle=r.get('driver_probe_and_runtime_cycle_complete'),genpd_lines=[s for s in genpd if any(x in s.lower() for x in ['titan','ac4b000','7-0010'])],mclk_lines=[s for s in clocks if 'cam_cc_mclk2_clk ' in s],direct_i2c_trace_saved=(host.PRIVATE/'front-r6-probe-trace-private.txt').exists(),fault_delta=r.get('fault_delta'))))

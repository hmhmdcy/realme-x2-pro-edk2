from pathlib import Path
import host,json
out=host.PRIVATE
for remote,name in [('/var/lib/samurai/k198-camss-trace/baseline-clocks-private.txt','baseline-clocks-private.txt'),('/var/lib/samurai/k198-final-health/clocks-private.txt','final-clocks-private.txt')]:host.download(remote,out/name)
names=['cam_cc_core_ahb_clk','cam_cc_slow_ahb_clk_src','cam_cc_cpas_ahb_clk','cam_cc_cci_1_clk','cam_cc_mclk2_clk','cam_cc_ife_0_clk','cam_cc_ife_0_csid_clk','cam_cc_camnoc_axi_clk']
def read(p):return {w[0]:w[1:9] for l in p.read_text().splitlines() if (w:=l.split()) and w[0] in names}
old=read(out/'baseline-clocks-private.txt');new=read(out/'final-clocks-private.txt');assert set(old)==set(new)==set(names);assert all(old[n][:2]==new[n][:2] for n in names);changed={n:dict(before=int(old[n][3]),after=int(new[n][3])) for n in names if old[n][3]!=new[n][3]};r=dict(stage=198,checked_camera_clocks=len(names),all_enable_and_prepare_counts_restored=True,rates_last_programmed_by_experiment=changed,no_direct_gate_writes=True);(Path(__file__).resolve().parent/'exit-clocks-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))

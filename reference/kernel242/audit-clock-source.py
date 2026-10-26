"""Record why RPMH debugfs Y and its nominal rate are not physical measurements."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel242')
K=Path('/home/cy122/pmos-samurai-kernel136/kernel')
sources={n:(K/n).read_text() for n in ['drivers/clk/clk.c','drivers/clk/qcom/clk-rpmh.c']}
core=sources['drivers/clk/clk.c'];rpmh=sources['drivers/clk/qcom/clk-rpmh.c']
ops=rpmh.split('static const struct clk_ops clk_rpmh_ops = {',1)[1].split('};',1)[0]
assert '.is_enabled' not in ops and '.enable' not in ops and '.prepare' in ops and '.recalc_rate' in ops
assert "else if (!c->ops->enable)\n\t\tseq_printf(s, \" %5c \", 'Y');" in core
assert 'RPMh clocks have a fixed rate. Return static rate.' in rpmh
manifest={n:hashlib.sha256(s.encode()).hexdigest() for n,s in sources.items()}
(P/'clock-source-audit-private.json').write_text(json.dumps(dict(manifest=manifest,rpmh_ops=ops),indent=2)+'\n')
report=dict(stage=242,rpmh_ops_has_no_hardware_is_enabled_callback=True,debugfs_Y_is_fallback_for_no_enable_callback=True,rpmh_rate_is_static_parent_rate_division=True,no_physical_xo_state_or_frequency_measurement=True)
(R/'clock-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

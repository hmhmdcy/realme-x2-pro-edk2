from pathlib import Path
import hashlib,json,subprocess
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference';k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
expected={}
for n in [156,157,158]:expected.update(json.loads((ref/f'kernel{n}/build-package-validation.json').read_text())['source_sha256'])
assert len(expected)==14
for n,h in expected.items():assert hashlib.sha256((k/n).read_bytes()).hexdigest()==h,n
panel=(k/'drivers/gpu/drm/panel/panel-samsung-sofef03f.c').read_text()
start=panel.index('static int sofef03f_on(');end=panel.index('static int sofef03f_supply_enable(',start)
init=panel[start:end]
assert 'mipi_dsi_dcs_write_seq_multi(&dsi_ctx, 0x51, 0x00, 0x00);' in init
assert 'return dsi_ctx.accum_err;' in init
prepare=panel[panel.index('static int sofef03f_prepare('):panel.index('static int sofef03f_enable(')]
assert 'ret = sofef03f_on(ctx);' in prepare and 'if (ret)\n\t\tsofef03f_power_off(ctx);' in prepare
bl=panel[panel.index('static int sofef03f_bl_update('):panel.index('static const struct backlight_ops')]
assert '!READ_ONCE(ctx->panel.backlight_ready)' in bl
r=subprocess.run(['git','apply','--reverse','--check',str(ref/'kernel158/display-fix-from154.patch')],cwd=k,capture_output=True)
assert r.returncode==0,r.stderr
report=dict(actual_kernel_build=158,all_14_current_source_hashes_match_compiled_builds=True,
    panel_init_explicit_zero_brightness_before_display_on=True,
    panel_init_command_errors_propagated_and_power_removed=True,
    early_positive_brightness_updates_blocked=True,consolidated_patch_reverse_check_pass=True,
    physical_startup_transition_feedback_still_required=True)
(ref/'kernel159/source-completion-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)

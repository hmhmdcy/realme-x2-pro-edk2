from pathlib import Path
import ast
r=Path('/mnt/e/RealmeX2Pro edk2')
ref=r/'reference/kernel135'
prior=r/'reference/kernel134'
t=(ref/'collect-rollback-runtime.sh').read_text().replace('k135-rollback132-runtime','k135-rollback132-final')
t=t.replace('K135_STABLE132_ROLLBACK_NATIVE_RUNTIME_CAPTURED','K135_STABLE132_AUTOMATIC_FINAL_RUNTIME_CAPTURED')
assert not (ref/'collect-rollback-final.sh').exists()
(ref/'collect-rollback-final.sh').write_text(t)
t=(prior/'inspect-recovered-runtime.py').read_text()
t=t.replace("out=Path('/mnt/e/edk2-samurai-out/kernel134')", "out=Path('/mnt/e/edk2-samurai-out/kernel135')")
t=t.replace("out/'recovered-runtime-private.tar.gz'", "out/'rollback-final-private.tar.gz'").replace('-k134+','-k132+').replace("b'#134 SMP PREEMPT'", "b'#132 SMP PREEMPT'")
t=t.replace("out/'source-boot-id-private.txt'", "out/'failed-boot-id-private.txt'")
t=t.replace("out/'boot-package-validation.json'", "r/'reference/kernel132/boot-package-validation.json'")
t=t.replace("out/'modules-k134-private.tar.gz'", "out.parent/'kernel132/modules-k132-private.tar.gz'").replace("out/'DTB-k134-private'", "out.parent/'kernel132/DTB-k132-private'")
start=t.index("node='/soc@0/spmi@c440000/pmic@2/usb-input@1300'")
end=t.index('report=dict(',start)
t=t[:start]+'''assert data['state.txt'].splitlines()[-1]==b'0' and data['phosh.txt'].strip() and data['phoc.txt'].strip()
assert data['gui-config-check.txt'].count(b': OK')==3
assert data['connector.txt'].strip()==b'connected'
assert b'active=1' in data['drm-state.txt']
assert b'freq: 5180' in data['wifi-link-private.txt']
assert b'at wcd934x_comp_probe' not in data['dmesg.txt']
assert b'at clk_core_disable' not in data['dmesg.txt']
assert b'at clk_core_unprepare' not in data['dmesg.txt']
assert b'ASoC error (-28)' not in data['dmesg.txt']
''' + t[end:]
t=t.replace('report=dict(initial_display_boot_failed=True,single_native_panel_reprobe_required=True,permanent_display_fix=False,usb_input_standard_power_supply_auto_registered=True,usb_input_attributes_read_only=True,', 'report=dict(stage=135,rollback_target=132,failed_candidate135_rejected=True,automatic_desktop_recovered_without_panel_reprobe_or_greetd_marker_change=True,permanent_display_fix=False,usb_input134_driver_currently_absent_after_rollback=True,original_gui_configuration_unchanged=True,codec_enospc_and_probe_warn_absent_this_boot=True,dsi_clock_warns_absent_this_boot=True,')
t=t.replace('embedded134_dtb_with_charger_verified','embedded132_dtb_with_charger_verified').replace('kernel_build=134','kernel_build=132').replace('boot_bytes_match_embedded134','boot_bytes_match_embedded132')
t=t.replace("r/'reference/kernel134/embedded-runtime-validation.json'", "r/'reference/kernel135/rollback-runtime-validation.json'")
ast.parse(t)
assert not (ref/'inspect-rollback-runtime.py').exists()
(ref/'inspect-rollback-runtime.py').write_text(t)
print('K135_STABLE132_FINAL_AUTOMATIC_DESKTOP_FULL_VERIFIER_READY',flush=True)

from pathlib import Path

ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel136')
old = (ref / 'prepare-gpu-evidence.sh').read_text()
new = old.replace('k136-gpu-vm-evidence', 'k136-legacy-vm-trace')
new = new.replace('k136-gpu-tools', 'k136-legacy-gpu-tools')
new = new.replace('k136-current132', 'k136-first-runtime')
new = new.replace('test "$(cat /proc/sys/kernel/tainted)" = 0',
    'test "$(cat /proc/sys/kernel/tainted)" = 512\n'
    'uname -v | grep -q "^#136 "\n'
    'test "$(dmesg | grep -c "WARNING:")" = 1\n'
    'dmesg | grep -q "at wcd934x_comp_probe"\n'
    'test "$(dmesg | grep -c "gpu fault:" || true)" = 0')
(ref / 'prepare-legacy-gpu-probe.sh').write_text(new)
old = (ref / 'capture-gpu-evidence.py').read_text()
new = old.replace('k136-gpu-vm-evidence', 'k136-legacy-vm-trace')
new = new.replace('k136-gpu-tools', 'k136-legacy-gpu-tools')
new = new.replace('k136-gpu-evidence', 'k136-legacy-evidence')
new = new.replace("assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'",
    "assert Path('/proc/sys/kernel/tainted').read_text().strip() == '512'")
new = new.replace("assert os.uname().release == '7.3.0-rc6-rmx1931-samurai-k132+'",
    "assert os.uname().release == '7.3.0-rc6-rmx1931-samurai-k132+'\n"
    "assert os.uname().version.startswith('#136 ')")
new = new.replace("capture(['dmesg'], 'dmesg-before-private.txt')",
    "capture(['dmesg'], 'dmesg-before-private.txt')\n"
    "d = (out / 'dmesg-before-private.txt').read_text()\n"
    "assert d.count('WARNING:') == 1 and 'at wcd934x_comp_probe' in d\n"
    "assert d.count('unable to prepare channel') == 31\n"
    "assert 'dsi_err_worker' not in d and 'Failed to read' not in d")
new = new.replace("(trace / 'buffer_size_kb').write_text('512')", "(trace / 'buffer_size_kb').write_text('1024')")
new = new.replace("'msm_gpu_submit_retired', 'msm_gpu_suspend', 'msm_gpu_resume']",
    "'msm_gpu_submit_retired', 'msm_gpu_suspend', 'msm_gpu_resume',\n"
    "          'msm_gpu_vm_update', 'msm_gpu_vm_switch_enqueue']")
new = new.replace('assert len(enabled_events) >= 7',
    "assert 'drm_msm_gpu/msm_gpu_vm_update' in enabled_events\n"
    "    assert 'drm_msm_gpu/msm_gpu_vm_switch_enqueue' in enabled_events")
new = new.replace("param.write_text('8')", "assert param.read_text().strip() == '0'")
new = new.replace("range(8)", "range(13)").replace("index < 7", "index < 12")
anchor = "    # Restore output state without repeatedly cycling the panel.\n"
start = new.index(anchor)
end = new.index("    capture(['dmesg'], 'dmesg-final-private.txt')", start)
new = new[:start] + "    # Keep the normally enabled output on for the delayed desktop observation.\n" + new[end:]
new = new.replace("(out / 'desktop-pids-final.json').write_text(json.dumps(pids()))",
    "try:\n        final_pids = pids()\n    except subprocess.CalledProcessError:\n        final_pids = {}\n"
    "    (out / 'desktop-pids-final.json').write_text(json.dumps(final_pids))\n"
    "    capture(['su', '-s', '/bin/sh', 'cy122', '-c',\n"
    "             'env XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0 wlr-randr'],\n"
    "            'output-final-private.txt', timeout=10, check=False)")
new = new.replace("display_output_previously_enabled=was_enabled, goal_complete=False)",
    "display_output_previously_enabled=was_enabled, output_kept_enabled=True,\n"
    "                  diagnostic_only_preexisting_audio_taint=512, goal_complete=False)")
new = new.replace("# This only allocates bounded history for newly created VMs. Existing\n    # desktop VMs and all shader/cache/flush/debug modes remain unchanged.",
    "# Legacy VM mapping events are traced; the VM_BIND log parameter stays at zero.")
(ref / 'capture-legacy-vm-trace.py').write_text(new)
compile(new, 'capture-legacy-vm-trace.py', 'exec')
print('K136_ONE_LEGACY_DIAGNOSTIC_PROBE_SCRIPTS_GENERATED_KNOWN_AUDIO_TAINT_EXPLICIT')

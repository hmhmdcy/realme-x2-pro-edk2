"""One host-only native-DT overlay/apply, followed by whole-tree raw comparison."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
if sys.flags.optimize:
    raise RuntimeError('Non-optimized interpreter required')
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
NATIVE = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/eud-boot-policy-private/samurai-eud-off-policy-private.dtb')
OUT = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/usb-input-irq-board-private-01')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
spec = importlib.util.spec_from_file_location('irq_board_fdt', HERE / 'inspect-dtb.py')
fdt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fdt)
PARENT = '/soc@0/spmi@c440000/pmic@2'
CHILD = PARENT + '/usb-input@1300'
OVERLAY = '''/dts-v1/;
/plugin/;

/ {
    fragment@0 {
        target-path = "/soc@0/spmi@c440000/pmic@2";
        __overlay__ {
            /* Repeat the existing parent cells only for dtc local checks.
             * The merged parent values must remain byte-for-byte equal.
             */
            #address-cells = <1>;
            #size-cells = <0>;
            usb-input@1300 {
                compatible = "realme,rmx1931-usb-input";
                reg = <0x1300>;
                interrupts = <0x2 0x13 0x4 0x3>, <0x2 0x13 0x6 0x1>;
                interrupt-names = "usbin-plugin", "usbin-src-change";
                status = "okay";
            };
        };
    };
};
'''


def main():
    assert sys.argv[1:] == ['--execute'], 'Explicit --execute required; never accesses a device'
    assert not OUT.exists(), 'Unique DT/pair directory exists; do not replay'
    assert not (HERE / 'dt-result.json').exists()
    assert sha(NATIVE) == '9271d9cc33b3701ad0675c6345d43e9a5c404aa6c192126edc3eb715b0914358'
    old = fdt.decode(NATIVE.read_bytes())
    assert CHILD not in old['nodes']
    assert old['nodes'][PARENT]['#address-cells'] == bytes.fromhex('00000001')
    assert old['nodes'][PARENT]['#size-cells'] == bytes.fromhex('00000000')
    OUT.mkdir(parents=True)
    commands = []
    result = {'passed': False, 'private_output': str(OUT), 'source_native_sha256': sha(NATIVE),
              'host_only': True, 'runtime_overlay_applied': False, 'SDK_Git_device_used': False,
              'script_sha256': sha(Path(__file__))}
    try:
        tools = {name: Path(shutil.which(name)).resolve() for name in ['dtc', 'fdtoverlay']}
        result['tools'] = {name: {'path': str(path), 'sha256': sha(path)} for name, path in tools.items()}
        for name, path in tools.items():
            p = subprocess.run([str(path), '--version'], capture_output=True)
            assert p.returncode == 0
            result['tools'][name]['version'] = (p.stdout + p.stderr).decode().strip()
        overlay = OUT / 'usb-input-irq.dtso'
        overlay.write_bytes(OVERLAY.encode())

        def run(name, argv):
            p = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = p.communicate()
            (OUT / (name + '.stdout')).write_bytes(out)
            (OUT / (name + '.stderr')).write_bytes(err)
            commands.append({'name': name, 'argv': argv, 'pid': p.pid, 'terminal': True, 'returncode': p.returncode,
                             'stdout_sha256': sha(OUT / (name + '.stdout')),
                             'stderr_sha256': sha(OUT / (name + '.stderr'))})
            assert p.returncode == 0, (name, err.decode())
            return err.decode()

        diagnostics = run('compile-overlay', [str(tools['dtc']), '-I', 'dts', '-O', 'dtb',
                          '-o', str(OUT / 'usb-input-irq.dtbo'), str(overlay)])
        # Standalone target-path overlays have no SPMI ancestor to walk. This
        # warning is retained, then separately checked in the merged full tree.
        if diagnostics:
            lines = diagnostics.splitlines()
            assert len(lines) == 1 and 'Warning (interrupts_property)' in lines[0] and 'Missing interrupt-parent' in lines[0], diagnostics
        run('apply-overlay', [str(tools['fdtoverlay']), '-i', str(NATIVE),
                            '-o', str(OUT / 'samurai-usb-input-irq-native-private.dtb'),
                            str(OUT / 'usb-input-irq.dtbo')])
        candidate = OUT / 'samurai-usb-input-irq-native-private.dtb'
        new = fdt.decode(candidate.read_bytes())
        assert set(new['nodes']) - set(old['nodes']) == {CHILD}
        assert not set(old['nodes']) - set(new['nodes'])
        assert all(new['nodes'][name] == props for name, props in old['nodes'].items())
        expected = {
            'compatible': b'realme,rmx1931-usb-input\0',
            'reg': bytes.fromhex('00001300'),
            'interrupts': bytes.fromhex('0000000200000013000000040000000300000002000000130000000600000001'),
            'interrupt-names': b'usbin-plugin\0usbin-src-change\0',
            'status': b'okay\0',
        }
        assert new['nodes'][CHILD] == expected
        assert new['reserves'] == old['reserves']
        assert all(new[key] == old[key] for key in ['boot_cpu', 'version', 'last_version'])
        assert new['nodes'][PARENT + '/typec@1500']['status'] == b'disabled\0'
        eud = {name: props for name, props in old['nodes'].items() if b'eud' in props.get('compatible', b'')}
        assert eud and all(new['nodes'][name] == props and props['status'] == b'disabled\0' for name, props in eud.items())
        # Reparse both merged and original with dtc as well; existing baseline
        # diagnostics are retained and cannot be attributed to the new child.
        old_diag = run('decompile-original', [str(tools['dtc']), '-I', 'dtb', '-O', 'dts',
                       '-o', str(OUT / 'native-original-private.dts'), str(NATIVE)])
        new_diag = run('decompile-candidate', [str(tools['dtc']), '-I', 'dtb', '-O', 'dts',
                       '-o', str(OUT / 'native-candidate-private.dts'), str(candidate)])
        assert 'usb-input@1300' not in new_diag
        normalize = lambda d, path: d.replace(str(path), '<dtb>').replace(str(OUT / 'native-original-private.dts'), '<dts>').replace(str(OUT / 'native-candidate-private.dts'), '<dts>')
        assert normalize(old_diag, NATIVE) == normalize(new_diag, candidate)
        assert sha(NATIVE) == result['source_native_sha256']
        result.update(passed=True, candidate_DTB_sha256=sha(candidate), candidate_DTB_bytes=candidate.stat().st_size,
                      overlay_source_sha256=sha(overlay), overlay_blob_sha256=sha(OUT / 'usb-input-irq.dtbo'),
                      old_node_count=len(old['nodes']), new_node_count=len(new['nodes']),
                      old_property_count=sum(map(len, old['nodes'].values())), existing_node_property_changes=[],
                      only_added_node=CHILD, added_properties={key: value.hex() for key, value in expected.items()},
                      reserve_table_unchanged=True, reserved_memory_subtree_unchanged=True,
                      bootcpu_and_FDT_versions_unchanged=True, EUD_and_TypeC_disabled_unchanged=True,
                      original_native_DTB_unchanged=True,
                      overlay_compile_context_diagnostics=diagnostics,
                      full_tree_diagnostics_equal_original=True,
                      original_full_tree_diagnostic_lines=len(old_diag.splitlines()))
    except BaseException as error:
        result['error'] = repr(error)
        raise
    finally:
        result['commands'] = commands
        (OUT / 'dt-result.json').write_text(json.dumps(result, indent=2) + '\n')
        (HERE / 'dt-result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({key: result.get(key) for key in ['passed', 'candidate_DTB_sha256',
                         'candidate_DTB_bytes', 'old_node_count', 'new_node_count', 'error']}))


if __name__ == '__main__':
    main()

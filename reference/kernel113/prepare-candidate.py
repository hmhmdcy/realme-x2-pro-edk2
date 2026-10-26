from pathlib import Path
import hashlib, json, shutil, subprocess, sys

baseline = Path('/home/cy122/pmos-samurai-kernel112')
stage = Path('/home/cy122/pmos-samurai-kernel113')
out = Path('/mnt/e/edk2-samurai-out/kernel113')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
resume = sys.argv[1:] == ['--resume-private-copy']
assert not sys.argv[1:] or resume
if resume:
    assert stage.exists() and out.exists()
    assert {p.name for p in stage.iterdir()} == {'kernel'}
    assert not list(out.iterdir())
    assert (stage / 'kernel/.config').read_bytes() == (baseline / 'kernel/.config').read_bytes()
else:
    assert not stage.exists() and not out.exists()
assert sha(baseline / 'kernel/arch/arm64/boot/Image') == sha(out.parent / 'kernel112/Image-startup')
assert sha(baseline / 'kernel/arch/arm64/boot/dts/qcom/sm8150-samurai.dtb') == sha(out.parent / 'kernel112/dtb-startup')
if not resume: out.mkdir(); stage.mkdir()
for name in ('kernel', 'initramfs'):
    source, destination = str(baseline / name), str(stage / name)
    if resume and name == 'kernel': source += '/.'
    flags = ['--update=older'] if resume and name == 'kernel' else []
    subprocess.run(['cp', '-a', '--reflink=auto', *flags, source, destination], check=True)
kernel = stage / 'kernel'
before = (kernel / '.config').read_text()
assert 'CONFIG_SAMURAI_SENSOR_POWER' not in before
after = before.replace(str(baseline / 'initramfs'), str(stage / 'initramfs'))
assert after != before
(out / 'config-before').write_text(before)
(kernel / '.config').write_text(after + '\nCONFIG_SAMURAI_SENSOR_POWER=y\n')
for name in ('samurai-sensor-power.c', 'samurai-sensor-power-seq.h'):
    shutil.copyfile(ref / name, kernel / 'drivers/misc' / name)
path = kernel / 'drivers/misc/Makefile'
path.write_text(path.read_text() + '\nobj-$(CONFIG_SAMURAI_SENSOR_POWER) += samurai-sensor-power.o\n')
path = kernel / 'drivers/misc/Kconfig'
text = path.read_text()
text = text.replace('menu "Misc devices"', '''menu "Misc devices"

config SAMURAI_SENSOR_POWER
    bool "Realme X2 Pro manual sensor supply bring-up"
    depends on ARCH_QCOM && OF && REGULATOR && REMOTEPROC && SYSFS
    help
      Manual, board-specific SSC supply test. Both rails remain unvoted
      until root explicitly enables the state attribute while SLPI is
      offline. No sensor firmware or service is started by this driver.
''')
path.write_text(text)
path = kernel / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'
text = path.read_text()
assert 'samurai_sensor_power' not in text
text += '''
/* Official board19781 SSC supplies; this consumer is manually activated. */
/ {
    samurai_sensor_power: sensor-power {
        compatible = "realme,samurai-sensor-power";
        vdd-supply = <&vreg_l7c_3p0>;
        vddio-supply = <&vreg_l8c_1p8>;
        remoteproc = <&remoteproc_slpi>;
    };
};
'''
path.write_text(text)
(out / 'preparation.json').write_text(json.dumps(dict(kernel_build=113, baseline=112,
    config_delta=['CONFIG_INITRAMFS_SOURCE','CONFIG_SAMURAI_SENSOR_POWER'],
    new_driver='drivers/misc/samurai-sensor-power.c', manual_activation=True,
    supplies=['PM8150L L7','PM8150L L8'], slpi_auto_boot=False,
    userdata_reformatted=False, candidate_deployed=False,
    intended_flash_partitions=['boot','logdump'], goal_complete=False), indent=2)+'\n')
print('KERNEL113_ISOLATED_MANUAL_SENSOR_SUPPLY_CANDIDATE_PREPARED; no device change')

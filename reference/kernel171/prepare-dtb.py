from pathlib import Path
import difflib, hashlib, json, os, shutil, subprocess

os.umask(0o077)
k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path(__file__).parent
out = Path('/mnt/e/edk2-samurai-out/kernel171')
out.mkdir(mode=0o700, exist_ok=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source = json.loads((ref.parent / 'kernel168/source-validation.json').read_text())
for name, digest in source['source_sha256'].items():
    assert sha(k / name) == digest, name
assert set(subprocess.check_output(['git', 'diff', '--name-only'], cwd=k, text=True).splitlines()) == set(source['modified_files'])
name = 'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'
before = (k / name).read_text()
assert before.count('qcom,sd-lines = <0>;') == 1
assert before.count('pins = "gpio137", "gpio138", "gpio139";') == 2
after = before.replace('qcom,sd-lines = <0>;', 'qcom,sd-lines = <1>;')
after = after.replace('pins = "gpio137", "gpio138", "gpio139";', 'pins = "gpio137", "gpio138", "gpio140";')
assert not (out / 'samurai-before168-private.dts').exists()
(out / 'samurai-before168-private.dts').write_text(before)
shutil.copyfile(k / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb', out / 'samurai-before168-private.dtb')
image_before = sha(k / 'arch/arm64/boot/Image')
config_before = sha(k / '.config')
(k / name).write_text(after)
patch = ('Subject: [PATCH] arm64: dts: samurai: route speaker MI2S RX over SD1\n\n'
         "The board's OEM quaternary MI2S RX mask selects SD1, carried on GPIO140.\n"
         'Use that data line and its matching active/sleep pin states so PCM reaches\n'
         'the two MAX98937 amplifiers. Keep their configuration and gain unchanged.\n\n---\n') + ''.join(
    difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile='a/' + name, tofile='b/' + name))
(ref / 'speaker-sd1.patch').write_text(patch)
env = os.environ.copy()
env.update(PATH='/home/cy122/.cargo/bin:' + env['PATH'], RUSTUP_HOME='/home/cy122/.rustup', KBUILD_BUILD_VERSION='168')
with (out / 'dtb-build-private.log').open('wb') as log:
    subprocess.run(['make', 'ARCH=arm64', 'CROSS_COMPILE=aarch64-linux-gnu-', '-j4', 'qcom/sm8150-samurai.dtb'],
                   cwd=k, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
dtb = k / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'
subprocess.run(['git', 'diff', '--check'], cwd=k, check=True)
assert sha(k / 'arch/arm64/boot/Image') == image_before
assert sha(k / '.config') == config_before
for name, digest in source['source_sha256'].items():
    assert sha(k / name) == digest
shutil.copyfile(dtb, out / 'samurai-sd1-k171-private.dtb')
report = dict(stage=171, kernel_build_kept=168, dtb_built=True, dtb_before_sha256=sha(out / 'samurai-before168-private.dtb'),
              dtb_after_sha256=sha(dtb), dts_after_sha256=sha(k / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'),
              image_unchanged_sha256=image_before, config_unchanged=True, audio_lifecycle_sources_unchanged=True,
              speaker_sd_line=1, data_pin=140, hardware_not_deployed=True)
for directory in [out, ref]:
    (directory / 'dtb-build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)

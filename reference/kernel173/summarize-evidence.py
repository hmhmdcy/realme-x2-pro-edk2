from pathlib import Path
import hashlib, json, os, subprocess, tarfile

ref = Path(__file__).parent; project = ref.parent.parent
out = Path('/mnt/e/edk2-samurai-out/kernel173')
def extract(folder):
    with tarfile.open(out / 'k173-all-private.tar.gz') as archive:
        return json.load(archive.extractfile(folder+'/validation.json'))
def save(name,value): (ref / name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
for folder,name in [('k173-ucm-test-v2','ucm-test-validation.json'),('k173-deploy-v2','deployment-validation.json'),
                    ('k173-single-card-recovery','single-card-recovery-validation.json'),
                    ('k173-silent-headset','silent-headset-pcm-validation.json'),('k173-final','final-validation.json')]:
    save(name,extract(folder))
final = extract('k173-final'); assert final['installed_ucm173_verified'] and final['single_pulse_card_and_alsa_module']
assert final['taint']==0 and all(v==0 for v in final['fault_counts'].values())
assert final['nv_verified'] and final['modules132_verified'] and final['final_amplifiers_off']
native = json.loads((ref / 'dmic0-ucm173-low24-analysis.json').read_text())
desktop = json.loads((ref / 'desktop-acoustic-validation.json').read_text())
assert all(d['known_tone_detected_with_disabled_amp_control'] for d in native['speaker_decisions'])
assert all(d['detected_with_native_amp_off_reference'] for d in desktop['results'])
save('acoustic-validation.json',dict(stage=173,kernel_build=172,native_cases=4,desktop_duplex_cases=2,
    native_left_right_correlations=[d['active_code_correlation'] for d in native['speaker_decisions']],
    native_amp_on_off_difference_db=[d['active_to_disabled_tone_band_db'] for d in native['speaker_decisions']],
    desktop_left_right_correlations=[d['best_code_energy_correlation'] for d in desktop['results']],
    desktop_paplay_and_parecord=True,source_and_sink_software_volume_and_mute_preserved=True,
    actual_headphone_and_headset_sound_not_tested=True))
save('user-availability.json',dict(date='2026-10-14',user_reply='暂时没有耳机',
    no_physical_headset_test_performed=True,continue_independent_software_verification=True))
# Verify the overlay installer on a Linux filesystem with real POSIX modes.
root = Path('/tmp/k173-rootfs-install-check'); assert not root.exists(); root.mkdir(mode=0o700)
subprocess.run(['python3',str(project/'linux-port/scripts/install-audio-ucm.py'),'--root',str(root)],check=True,stdout=subprocess.DEVNULL)
names = ['usr/libexec/samurai-audio-route','usr/share/alsa/ucm2/conf.d/Realme_X2_Pro/HiFi.conf',
         'usr/share/alsa/ucm2/conf.d/Realme_X2_Pro/Realme_X2_Pro.conf']
manifest = json.loads((ref / 'source-validation.json').read_text())['sha256']
for n in names:
    source_name = 'samurai-audio-route.py' if n.endswith('samurai-audio-route') else Path(n).name
    p = root/n; assert hashlib.sha256(p.read_bytes()).hexdigest() == manifest[source_name]
    assert p.stat().st_mode & 0o777 == (0o755 if n.endswith('samurai-audio-route') else 0o644)
    assert all(parent.stat().st_mode & 0o555 == 0o555 for parent in p.parents if parent != root and parent.is_relative_to(root))
k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
kernel = json.loads((ref.parent/'kernel172/kernel-build-validation.json').read_text())
for n,digest in kernel['source_sha256'].items(): assert hashlib.sha256((k/n).read_bytes()).hexdigest()==digest
assert hashlib.sha256((k/'arch/arm64/boot/Image').read_bytes()).hexdigest()==kernel['image_sha256']
assert hashlib.sha256((k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb').read_bytes()).hexdigest()==kernel['dtb_sha256']
save('current-source-validation.json',dict(stage=173,kernel_build=172,kernel_source_and_image_and_dtb172_unchanged=True,
    ucm173_manifest=manifest,staged_rootfs_files_verified=names,staged_posix_permissions_verified=True,
    installer_sha256=hashlib.sha256((project/'linux-port/scripts/install-audio-ucm.py').read_bytes()).hexdigest()))
print('K173_EVIDENCE_AND_STAGED_OVERLAY_VERIFIED',flush=True)

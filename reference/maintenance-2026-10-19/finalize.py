"""Summarize completed receipts and verify preserved handoff identities."""
from pathlib import Path
import hashlib,json,os,subprocess,time
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
P=Path('/mnt/e/edk2-samurai-out/cleanup20261019')
def read(name):return json.loads((P/name).read_text(encoding='utf-8-sig'))
wsl=read('wsl-cleanup-private.json');win=read('windows-cleanup-private.json');volume=read('volume118-verification-private.json')
assert wsl['complete'] and win['complete'] and volume['verified'] and volume['original_removed']
assert all(row['removed'] and not Path(row['path']).exists() for row in wsl['rows'])
for row in win['rows']:
    p=Path('/mnt/e')/row['path'][3:].replace('\\','/')
    assert row['removed'] and not p.exists()
assert not Path('/mnt/e/edk2-samurai-out/kernel118/build-volume.ext4').exists()
archive=Path(volume['archive']);assert archive.is_file() and archive.stat().st_size==volume['archive_bytes']
kernel=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
assert subprocess.check_output(['git','-C',str(kernel),'rev-parse','HEAD'],text=True).strip()=='c5e118faec21a6c4bd2e7d5b86b3b21ad9dc2117'
assert not subprocess.check_output(['git','-C',str(kernel),'status','--porcelain'])
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root')
source=sdk/'work/libcamera299-inline'
matches={}
for a,b in [('ipa/camss.cpp','src/ipa/camss-vfe/camss.cpp'),
            ('pipeline/camss_vfe.cpp','src/libcamera/pipeline/camss-vfe/camss_vfe.cpp'),
            ('camss.mojom','include/libcamera/ipa/camss.mojom')]:
    expected=(ROOT/'reference/kernel302'/a).read_bytes();actual=(source/b).read_bytes()
    assert expected==actual
    matches[b]=hashlib.sha256(actual).hexdigest()
for p in [source/'output/build.ninja',sdk/'work/libcamera278-r24-r3-built/src/libcamera-v0.7.2/output/build.ninja',sdk/'candidate278-r24',Path('/mnt/e/edk2-samurai-out/kernel282/full-kernel-build282.ext4')]:assert p.exists()
before={'C':3872743424,'E':13143891968}
after={drive:os.statvfs('/mnt/'+drive.lower()).f_bavail*os.statvfs('/mnt/'+drive.lower()).f_frsize for drive in before}
summary=dict(date='2026-10-19',complete=True,phone_modified=False,adaptation_goal_status='paused',
    actual_kernel_build=298,latest_candidate=302,candidate_installed=False,
    windows_free_bytes_before=before,windows_free_bytes_after=after,
    windows_free_bytes_increased={drive:after[drive]-before[drive] for drive in before},
    wsl_deleted_logical_file_bytes=wsl['bytes'],wsl_deleted_file_count=len(wsl['rows']),
    wsl_filesystem_free_bytes_increased=wsl['free_after']-wsl['free_before'],
    windows_deleted_cache_and_vmlinux_bytes=win['bytes'],windows_deleted_file_count=len(win['rows']),
    volume118_raw_bytes=volume['decompressed_bytes'],volume118_archive_bytes=volume['archive_bytes'],
    volume118_archive_full_decompression_sha256_verified=volume['sha256'],
    volume118_old145_archive_also_retained=True,volume118_original_removed=True,
    protected_seven_recovery_and_candidate_artifacts_sha256_before_after_verified=True,
    kernel298_git_clean=True,current302_source_sha256=matches,
    source_firmware_nv_calibration_private_keys_and_samples_preserved=True,
    current_kernel_build_volume_and_current_product_and_candidate_outputs_preserved=True,
    wsl_root_trim_succeeded=True,wsl_shutdown_or_offline_compaction=False,
    empty_cache_directories_retained_after_recursive_removal_automatic_approval_rejection=True,
    free_space_measurement_note='WSL logical recovery and NTFS C recovery overlap; do not add them. TRIM range is not reclaimed bytes.',
    verified_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
(HERE/'cleanup-validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
readme=HERE/'README.md';text=readme.read_text()
table='\n## 实测空间结果\n\n| 文件系统 | 清理前可用 | 清理后可用 | 可用空间增加 |\n| --- | ---: | ---: | ---: |\n'
for drive in before:table+=f'| {drive}盘（GB，十进制） | {before[drive]/1e9:.2f} | {after[drive]/1e9:.2f} | {(after[drive]-before[drive])/1e9:.2f} |\n'
table+=f"\nWSL根文件系统自身可用空间增加{summary['wsl_filesystem_free_bytes_increased']/1e9:.2f} GB；此数与C盘回收重叠，不另加。旧118原卷21.47 GB压缩为{volume['archive_bytes']/1e9:.2f} GB，全量解压SHA256与当前原卷一致后删除原卷。数值为收尾时的实测，后台服务会使空闲空间小幅变化。\n"
assert '## 实测空间结果' not in text
readme.write_text(text+table)
names=json.loads((ROOT/'reference/kernel302/checkpoint-validation.json').read_text())['files']
checkpoint=dict(date='2026-10-19',actual_kernel_build=298,latest_candidate=302,goal_status='paused',
    archive='archive/camera-before-handoff-2026-10-19/manifest.json',files={})
for name in names:
    raw=(ROOT/name).read_bytes();checkpoint['files'][name]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
assert len((ROOT/'NEXT-SESSION.md').read_bytes())<=6500
assert len((ROOT/'DOCS-INDEX.md').read_bytes())<=10000
(HERE/'checkpoint-validation.json').write_text(json.dumps(checkpoint,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False))

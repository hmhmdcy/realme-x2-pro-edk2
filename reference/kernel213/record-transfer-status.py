from pathlib import Path
import json
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel213')
record=json.loads((private/'final-evidence-manifest-private.json').read_text());partial=private/'final-evidence-private.tar.gz'
assert partial.stat().st_size<record['size'] and not (here/'final-evidence-archive-validation.json').exists()
report=dict(stage=213,native_private_archive_created=True,native_manifest_regular_files=len(record['files']),host_archive_download_complete=False,host_partial_archive_kept_private=True,whole_archive_and_member_verification_pending=True,isolated_sdk_and_ipa_private_key_excluded=True,candidate_binaries_and_build_logs_in_native_archive=True,raw_scene_images_and_logs_kept_private=True,initial_one_mib_usb_transfer_truncated=True,later_usb_small_ssh_timed_out=True,strict_original_key_wifi_twice_verified_same_boot_and_taint_zero=True,later_windows_and_native_wifi_archive_reads_failed_or_timed_out=True,latest_full_health_recheck_not_responsive=True,no_blind_reboot_usb_reset_or_partition_operation=True,last_verified_full_health='final-health-validation.json',latest_recheck='health-after-transfer-failure-validation.json')
(here/'final-evidence-archive-validation.json').write_text(json.dumps(report,indent=2)+'\n')
path=here/'README.md';text=path.read_text();old='私人证据归档包括候选二进制、构建/失败日志及场景文件，排除SDK和IPA私钥，逐成员核对。'
assert old in text;text=text.replace(old,'手机已生成含227份文件的私人归档及逐文件清单，包括候选二进制、构建/失败日志和场景文件，排除SDK和IPA私钥。但主机下载在第三个1MiB块截断，完整下载和逐成员核对尚未完成；不能把本轮归档写成验收通过。')
marker='下一步把三个补丁整合进可复现相机包并部署'
assert marker in text;text=text.replace(marker,'USB截断后小SSH超时；Wi-Fi通过原密钥两次核验同一启动/taint0，随后Windows及WSL原生SSH归档取回均失败或超时，最新完整健康复查也未响应。前述完整健康样本发生于传输故障之前，不能冒充故障后的当前状态；未执行盲目重启、USB复位或分区操作。[最新复查](health-after-transfer-failure-validation.json)。\n\n下一步先恢复新鲜连接，并在宿主继续准备原包功能完整的构建；然后把三个补丁整合进可复现相机包并部署')
path.write_text(text)
path=repo/'NEXT-SESSION.md';text=path.read_text();marker='归档完整留在手机，回收状态以213归档报告为准，USB/Wi-Fi稳定性未修。'
assert marker in text;text=text.replace(marker,'手机归档227文件仍待完整回收，主机只有截断副本；Windows/原生Wi-Fi读回及最后完整健康复查未响应。此前相机/三DSP完整健康样本在传输故障之前，两次Wi-Fi guard样本仅证明当时同boot/taint0。任何设备变更前先恢复新鲜连接；不要盲目重启或复位。回收状态见[213归档报告](reference/kernel213/final-evidence-archive-validation.json)，USB/Wi-Fi稳定性未修。')
path.write_text(text)
path=repo/'linux-port/docs/HARDWARE-STATUS.md';text=path.read_text();lines=text.splitlines();index=next(i for i,line in enumerate(lines) if line.startswith('| 普通USB与OTG |'))
lines[index]=lines[index].replace('203 USB大传输稳定性仍未修复；','213再次1MiB分块截断、后续USB小SSH超时，原密钥Wi-Fi两次同boot可达后也无法完成归档/最终健康复查，未盲目复位；大传输/当前连通性仍未解决；')
path.write_text('\n'.join(lines)+'\n')
plan=json.loads((private/'current-work-private.json').read_text());plan.update(state='213 dark RAW and fixed-white A/B first-frame fix verified before transfer failure. Native227-file archive generated, host copy truncated and whole/member verification pending. USB small SSH failed; Wi-Fi twice same-boot/taint0 then archive transfer and latest full-health check failed. No reset/reboot/flash sent. Installed camera libraries/database unchanged at last verified state.',next='Restore fresh strictly authenticated connection and213 guard before any device mutation; no blind reset/reboot or repeating failed transfer generation. Continue host-side full original-feature camera package/source preparation independently. Private SDK/build retained; candidate3-pipeline binaries not suitable as complete system package. Native archive remains /tmp/k213-final-evidence-private.tar.gz with private manifest; verify entire archive and every member after recovery. Full peripheral goal remains active.')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(report))

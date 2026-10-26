from pathlib import Path
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel130'
s=(r/'reference/kernel129/quiesce-current128.sh').read_text()
s=s.replace('before=/var/lib/samurai/k129-preflash','before=/var/lib/samurai/k130-service-checkpoint').replace('dest=/var/lib/samurai/k129-quiesce','dest=/var/lib/samurai/k130-quiesce').replace("'^#128 '","'^#129 '")
s=s.replace('test "$(cat "$before/new-release.txt")" = 7.3.0-rc6-rmx1931-samurai-k129+', 'test "$(uname -r)" = 7.3.0-rc6-rmx1931-samurai-k129+')
s=s.replace('for service in greetd chronyd networkmanager', 'for service in bluetooth greetd chronyd networkmanager')
s=s.replace('sha256sum -c "$before/partition-check.sha256"','sha256sum -c "$before/partitions.sha256"').replace('sha256sum -c "$before/new-module-tree.sha256"','sha256sum -c /var/lib/samurai/k129-preflash/new-module-tree.sha256')
s=s.replace('/tmp/k129-quiesce-private.tar','/tmp/k130-quiesce-private.tar').replace('K129_CURRENT128_GUI_DRM_AUDIO_RADIO_QUIESCE_COMPLETE','K130_CURRENT129_WARM_REBOOT_QUIESCE_COMPLETE')
assert not (ref/'quiesce-current129.sh').exists();(ref/'quiesce-current129.sh').write_text(s)
s=(r/'reference/kernel129/verify-quiesce.py').read_text().replace('reference/kernel129','reference/kernel130').replace('out/kernel129','out/kernel130').replace("(out/'source-boot-id-private.txt')", "(out/'source-boot-id-private.txt')")
s=s.replace('current_kernel=128,target_kernel=129','current_kernel=129,target_kernel=129').replace('K129_CURRENT128_FULL_QUIESCE_ARCHIVE_GUARD_PASS','K130_CURRENT129_WARM_REBOOT_QUIESCE_GUARD_PASS')
assert not (ref/'verify-quiesce.py').exists();(ref/'verify-quiesce.py').write_text(s)
print('K130_WARM_REBOOT_TOOLS_PREPARED')

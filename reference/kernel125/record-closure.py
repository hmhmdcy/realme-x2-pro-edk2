from pathlib import Path
import json,ast
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel125';h=json.loads((ref/'host-volume-validation.json').read_text())
assert h['rootfs122_unmounted'] and h['kernel118_unmounted'] and all(x['offline_readonly_fsck_exit']==0 for x in h['volumes'])
line=f"125收尾：E122与E118构建卷均已同步卸载，离线只读fsck均0；E122内部余{h['volumes'][0]['inner_volume_free_bytes_before_unmount']:,} bytes。C可用{h['host_c_free_bytes']/1024**3:.2f}GiB，E宿主可用{h['host_e_free_bytes']/1024**3:.2f}GiB；原WSL VHD未resize/fsck，回退和已验rootfs全部保留。goal active。"
for name in ['NEXT-SESSION.md','sessions/125-native-cpas-qos-full-iova-window-and-mount-serialization.md']:
 p=r/name;t=p.read_text();assert '125收尾：' not in t;p.write_text(t+'\n'+line+'\n')
for p in [r/'reference/kernel118/ensure-build-volume.py',r/'reference/kernel122/ensure-rootfs-volume.py']:ast.parse(p.read_text())
p=ref/'syntax-validation.json';s=json.loads(p.read_text());s.update(shared_mount_helpers_ast_checked=2,powershell_collect_health_parser_pass=True);p.write_text(json.dumps(s,indent=2)+'\n')
print('K125_DOCS_OFFLINE_FSCK_BOTH_ZERO_AND_SPACE_CLOSURE_RECORDED')

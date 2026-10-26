from pathlib import Path
import json
r=Path('/mnt/e/RealmeX2Pro edk2');out=Path('/mnt/e/edk2-samurai-out/kernel126')
for folder in [r/'reference/kernel126',out]:
 p=folder/'complete-bundle-validation.json';b=json.loads(p.read_text());b.update(rootfs_home_ownership_matches_passwd=False,rootfs_semantic_owner_fix_required=True,rootfs_bulk_deployable=False,superseding_rootfs_generation=127);p.write_text(json.dumps(b,indent=2)+'\n')
for name in ['sessions/126-tpg-dma-guards-full-rootfs-and-real-deployment.md','NEXT-SESSION.md']:
 p=r/name;t=p.read_text().replace('home及145条目仍1000','home及60条目仍1000，另85个系统配置/固件资源属主1000').replace('145条目的属主','60个home与85个系统资源条目的属主').replace('127副本只修正这145条目的属主','127副本修正60个home及85个系统资源条目的属主').replace('145项ownership修正','60个home及85个系统资源ownership修正');p.write_text(t)
print('K126_ROOTFS_SEMANTIC_GAP_MARKED_DO_NOT_BULK_DEPLOY_SUPERSEDED_BY127')

"""Offline source/archive facts for the rollback design; no runtime material."""
from pathlib import Path
import ast
import hashlib
import io
import json
import tarfile
HERE=Path(__file__).resolve().parent
REF=HERE.parent.parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()


def main():
    paths={
      'stage':REF/'charging-ui-audit-20261023/usb-irq-protection-stage-candidate/stage-worker.py',
      'manager':REF/'charging-session-20261023/r8-source-integration/rootfs-sources/usr/sbin/samurai-charging',
      'live':REF/'charging-session-20261023/r8-source-integration/rootfs-sources/usr/lib/samurai-charging/live-session.py',
      'protection':HERE.parent/'protection-query-observer-candidate/samurai-gauge-protection.c',
      'stage_proof':HERE.parent/'irq-cohort-postboot-host-candidate/stage-proof.py',
      'completion':HERE.parent/'usb-irq-protection-fastboot-candidate/completion-proof.py'}
    required={'stage':'47794e53b8f31e974a968cb6610c69a49e456042be940bca7104bb182595c83a',
      'manager':'61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4',
      'live':'2199d7d413b2f4a5aeaa8270c20e967f5da711397c29e959e59463c1a5715f2b',
      'stage_proof':'85c9cd2b728a547ba434322d47cc15d4aeb228ae77afebeb7edff1bd0422e093',
      'completion':'d4a7b29c3f5978c1254c4b7c40376fbf12453057d4ba8cc98cbb4ef7a952be00'}
    sources={}
    wanted={'stage':{'atomic_replace','healthy','safe_sample','stage'},
            'manager':{'loaded_matches','verify','inhibit','command'},
            'live':{'registers','state'},'stage_proof':{'review_stage','guard_stage_fields'},
            'completion':{'review_action','review_completed_activation'}}
    for name,path in paths.items():
        raw=path.read_bytes();digest=sha(raw)
        if name in required:assert digest==required[name],name
        row=dict(path=str(path.resolve()),sha256=digest,bytes=len(raw))
        if name in wanted:
            text=raw.decode();tree=ast.parse(text)
            row['functions']={node.name:dict(line=node.lineno,end_line=node.end_lineno,
                sha256=sha(ast.get_source_segment(text,node).encode())) for node in tree.body
                if isinstance(node,ast.FunctionDef) and node.name in wanted[name]}
            assert set(row['functions'])==wanted[name]
        sources[name]=row
    archive=Path('E:/edk2-samurai-out/charging-management-20261023/usb-irq-protection-cohort-private-01/rollback-r8-payload.tar.gz')
    raw=archive.read_bytes();assert len(raw)==44194 and sha(raw)=='5ecae1f5799a1c01d132553b1ad4fb5923d643d1e13fcde8007f5380253fa339'
    targets={
        'lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko':'7d4e0f948b993a6e0cc9459bac4ade2db2fe7b88ce7b7d462ea34bcb933c4f70',
        'lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-gauge-protection.ko':'75b97e0d6b906ec600171ce68adec6f25a91556758f76bbf3d563cf831e783c7',
        'usr/share/samurai-charging/manifest.json':'320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'}
    members={}
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tar:
        assert len(tar.getmembers())==3
        for item in tar.getmembers():
            assert item.name in targets and item.name not in members and item.isfile()
            assert item.mode==0o600 and item.uid==item.gid==item.mtime==0 and item.uname==item.gname=='root' and not item.pax_headers
            data=tar.extractfile(item).read();assert sha(data)==targets[item.name]
            members[item.name]=dict(sha256=sha(data),bytes=len(data),mode='0600')
    result=dict(design_only=True,offline_source_and_rollback_archive_check_passed=True,
        sources=sources,archive=dict(path=str(archive),bytes=len(raw),sha256=sha(raw),members=members),
        design_sha256=sha((HERE/'DESIGN.md').read_bytes()),implementation_created=False,
        runtime_request_guard_or_identity_generated=False,device_SSH_USB_PM_SDK_Git=False,
        tests_or_builds_run=False)
    with (HERE/'design-evidence.json').open('x') as file:file.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,design_only=True,archive_members=len(members),actual_runtime_request_generated=False)))


if __name__=='__main__':main()

"""Inspect the exact common-framework source; do not patch proxy-link warnings."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';relative='drivers/base/core.c';raw=(source/relative).read_bytes();text=raw.decode();lines=text.splitlines()
old=subprocess.check_output(['git','-C',str(source),'show','ba61a62293e0f6bc5838c06f2e85e033e3d702a8:'+relative])
assert raw==old
needle='Failed to create device link (0x%x) with supplier';line=next(i+1 for i,s in enumerate(lines) if needle in s)
assert 'flags = FW_DEVLINK_FLAGS_PERMISSIVE' in text and 'ret = -EINVAL;' in '\n'.join(lines[line:line+4])
report=dict(stage=371,source=relative,source_sha256=hashlib.sha256(raw).hexdigest(),source_matches_actual_image363_commit=True,
 failure_log_line=line,proxy_flags_path_present=True,failure_branch_sets_einval=True,
 warning_alone_not_device_link_use_after_free_or_reset_proof=True,framework_patch_applied=False,
 primary_discussion='https://lists.openwall.net/linux-kernel/2026/09/29/1980',
 primary_discussion_scope='Different SoC: SYNC_STATE_ONLY proxy-link refusal after consumer probe; not a Realme ICP fix',passed=True)
(HERE/'framework-audit-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

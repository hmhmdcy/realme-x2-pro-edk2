from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2')
base=(root/'reference/kernel117/audit-public.py').read_text()
base=base.replace('for stage in [114,115,117]:','for stage in [114,115,117,118]:')
base=base.replace("'sessions/117-parser-boundaries-and-same-boot-desktop-recovery.md']","'sessions/117-parser-boundaries-and-same-boot-desktop-recovery.md','sessions/118-final-reset-read-build-and-host-space-recovery.md']")
base=base.replace('range(109,118)','range(109,119)')
base=base.replace('offline_candidate=116,','offline_camera_candidate=116,offline_display_candidate=118,')
base=base.replace("reference/kernel117/public-audit.json","reference/kernel118/public-audit.json")
exec(compile(base,'reused-public-auditor-118','exec'),{})

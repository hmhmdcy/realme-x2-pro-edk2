"""Cache relevant existing PM implementation excerpts, without source edits."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'kernel284'))
import storage

source = storage.mounted_build().parent / 'source354'
paths = {'kernel/power/wakeup.c': ['bool pm_wakeup_pending', 'bool pm_save_wakeup_count'],
         'kernel/power/main.c': ['static ssize_t wakeup_count_store'],
         'kernel/power/suspend.c': ['int pm_suspend(', 'static int enter_state(', 'pm_wakeup_pending()'],
         'drivers/base/power/wakeup.c': ['bool pm_wakeup_pending', 'bool pm_save_wakeup_count']}
result = {}
for name, patterns in paths.items():
    path = source / name
    if not path.exists():
        continue
    data = path.read_bytes()
    text = data.decode()
    excerpts = []
    for pattern in patterns:
        position = text.find(pattern)
        if position >= 0:
            excerpts.append({'pattern': pattern, 'line': text.count('\n', 0, position) + 1,
                             'text': text[max(0, position - 50):position + 1700]})
    result[name] = {'sha256': hashlib.sha256(data).hexdigest(), 'excerpts': excerpts}
(ROOT / 'pm-kernel-excerpts.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))

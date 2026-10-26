"""Read the original guarded build and saved W=1 command; no compiler invocation."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
helper = HERE.parents[1] / 'kernel284/storage.py'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert os.geteuid() == 0
assert sha(helper) == '5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'
spec = importlib.util.spec_from_file_location('bq_notify_storage284', helper)
storage = importlib.util.module_from_spec(spec); spec.loader.exec_module(storage)
shared = storage.mounted_build()
old = Path('/home/cy122/charging-management-20261023/gauge-current-samurai-candidate/kbuild')
command = old / 'drivers/power/supply/.bq27xxx_battery.o.cmd'
text = command.read_text()
row = next(line for line in text.splitlines() if line.startswith(('savedcmd_', 'cmd_')) and ':=' in line)
result = {'shared_build': str(shared), 'saved_private_build': str(old),
          'command_path': str(command), 'command_sha256': sha(command), 'saved_command': row,
          'original_source_sha256': sha(shared.parent / 'source354/drivers/power/supply/bq27xxx_battery.c'),
          'private_config_sha256': sha(old / '.config'), 'shared_config_sha256': sha(shared / '.config'),
          'compiler_invoked': False}
(HERE / 'command-inspection.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))

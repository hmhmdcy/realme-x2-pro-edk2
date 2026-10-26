from pathlib import Path
import json
import os
import subprocess

assert os.uname().version.startswith('#140 ')
d = subprocess.check_output(['dmesg'], text=True)
report = dict(kernel_build=140, taint=int(Path('/proc/sys/kernel/tainted').read_text()),
              phosh_present=subprocess.run(['pgrep', '-x', 'phosh'], capture_output=True).returncode == 0,
              phoc_present=subprocess.run(['pgrep', '-x', 'phoc'], capture_output=True).returncode == 0,
              counts={name: d.count(pattern) for name, pattern in [('gpu_faults', 'gpu fault:'),
                ('dpu_timeouts', 'frame done timeout'), ('dsi_errors', 'dsi_err_worker'),
                ('warnings', 'WARNING:'), ('tx_dma_errors', 'unable to prepare channel')]})
print(json.dumps(report, indent=2))

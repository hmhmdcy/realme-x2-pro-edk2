from pathlib import Path
import re

root = Path('/home/cy122/pmos-samurai-kernel136/kernel/drivers/gpu/drm/msm/disp/dpu1')
for name, pattern in [('dpu_encoder.c', 'frame_done_timeout|frame_done_callback|frame_done_timer|watchdog|resource_control|prepare_for_kickoff|kickoff_phys'),
                      ('dpu_encoder_phys_cmd.c', 'pp_tx_done|prepare_for_kickoff|pending_kickoff|autorefresh|enable_te|connect_te|enable.*irq|_wait_for')]:
    lines = (root / name).read_text().splitlines()
    print(name)
    for number, line in enumerate(lines, 1):
        if re.search(pattern, line):
            print(f'{number}: {line}')

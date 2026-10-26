from pathlib import Path
import ast

ref=Path(__file__).parent
s=(ref/'test-reprobe.py').read_text().replace('k175-reprobe','k175-reprobe-v2')
s=s.replace('        unsuspend();time.sleep(3);assert pcm_closed();amps_off()', '''        unsuspend()
        # PulseAudio suspend-on-idle normally waits five seconds after resume.
        for idle_sample in range(24):
            if pcm_closed():break
            time.sleep(.5)
        assert pcm_closed();amps_off()''')
ast.parse(s);(ref/'test-reprobe-v2.py').write_text(s)
print('K175_REPROBE_IDLE_WAIT_CORRECTED',flush=True)

from pathlib import Path
import ast

here=Path(__file__).resolve().parent;out=here/'reboot-r2'
source=(here/'inspect-desktop-session.py').read_text().replace('k202-runtime','k202r2-runtime')
ast.parse(source);(out/'inspect-desktop-session.py').write_text(source)
source=(here/'test-geoclue-after-reboot.py').read_text().replace('k202-runtime','k202r2-runtime').replace('k202-geoclue-reboot-test','k202r2-geoclue-first-session')
source=source.replace("(out/'watch-before-private.json').write_text", "assert watch_before['time_prepared'] and watch_before['time_preparation_starts']==watch_before['time_preparation_completions']>=1\n(out/'watch-before-private.json').write_text")
source=source.replace("new_boot_verified=True,", "new_boot_verified=True,first_session_after_automatic_idle_utc=True,idle_utc_preparation=watch_before['time_preparation_last_result'],idle_utc_preparation_attempts=watch_before['time_preparation_starts'],")
ast.parse(source);(out/'test-geoclue-first-session.py').write_text(source)
source=(here/'deploy-desktop-test.py').read_text().replace("here.parent/'kernel201/", "here.parent.parent/'kernel201/")
(out/'deploy-desktop-test.py').write_text(source)
print('Prepared first-session GNSS-only test on the next boot; no device operation.')

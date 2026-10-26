from pathlib import Path
import ast

here=Path(__file__).resolve().parent
source=(here.parent/'kernel185/test-powered-suspend.py').read_text().replace('k185-reboot-runtime/boot-id-private.txt','k204-runtime/boot-id-private.txt').replace('k185-bt-pm','k204-bt-pm').replace('stage=185','stage=204')
source=source.replace("report = dict(stage=204,", "report = dict(stage=204, uart_rx_wake_enabled=Path('/sys/bus/platform/devices/c8c000.serial/power/wakeup').read_text().strip()=='enabled', slpi_offline_from_recorded_startup_failure=True,")
ast.parse(source);(here/'test-powered-suspend.py').write_text(source)
source=(here.parent/'kernel185/setup-postboot-scan-policy.py').read_text().replace('k185-reboot-runtime/boot-id-private.txt','k204-runtime/boot-id-private.txt').replace('k185post-policy','k204-bt-policy').replace('main.conf.k185post-new','main.conf.k204-new')
ast.parse(source);(here/'setup-scan-policy.py').write_text(source)
print('Prepared explicit no-reconnect policy and one bounded powered RTC suspend.')

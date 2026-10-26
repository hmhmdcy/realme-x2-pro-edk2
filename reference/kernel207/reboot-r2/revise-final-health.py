from pathlib import Path
import ast

here=Path(__file__).resolve().parent
source=(here/'final-health.py').read_text().replace("out = root / 'k207r2-final-health'", "out = root / 'k207r2-final-health-r2'")
source=source.replace('same_second207_boot_verified=True,', 'same_second207_boot_verified=True,initial_final_health_observation_failed=True,')
ast.parse(source)
(here/'final-health-r2.py').write_text(source)
print('Prepared independent final observation. Initial assertion failure and directory preserved.')

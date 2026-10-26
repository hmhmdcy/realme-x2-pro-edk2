"""Reuse only R1 kernel/IO fixtures, not the old seven test groups."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;R1=HERE.parent/'pd5v-owner-feasibility'
raw=(R1/'test-control.c').read_bytes();s=raw.decode()
prefix=s[:s.index('static void bad_join')]
prefix=prefix.replace('static int joined;\n','')
prefix=prefix.replace(',wrong_device={.of_node=&other_node}','')
prefix=prefix.replace('static void mutex_unlock(struct mutex *m) { assert(m->held);m->held=0; }',
 'static void context_unlock_hook(struct mutex *m);\nstatic void mutex_unlock(struct mutex *m) { assert(m->held);m->held=0;context_unlock_hook(m); }')
reset=s[s.index('static void reset(void)'):s.index('static struct samurai_pd5v *create(void)')]
reset=reset.replace('power_enable_error=joined=free_count','power_enable_error=free_count')
probe=s[s.index('/* Full actual qcom probe'):s.index('static void probe_case_cleanup')]
(HERE/'kernel-boundary-fixture.inc').write_bytes((prefix+'\n'+reset+'\n'+probe).encode())
(HERE/'fixture-provenance.json').write_text(json.dumps(dict(original_fixture=str(R1/'test-control.c'),original_sha256=hashlib.sha256(raw).hexdigest(),
 reused='kernel/OF/regmap/regulator boundary definitions plus reset and unchanged probe fakes only',
 adaptations=['mutex-unlock interleave hook','remove obsolete old-group counter'],old_groups_included=False,old_groups_executed=False),indent=2)+'\n')

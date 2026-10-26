from pathlib import Path
import copy, hashlib, importlib.util, json, tarfile

ref = Path(__file__).parent
out = Path('/mnt/e/edk2-samurai-out/kernel173')
source = ref.parent.parent / 'linux-port/scripts/samurai-audio-route.py'
spec = importlib.util.spec_from_file_location('route',source)
route = importlib.util.module_from_spec(spec); spec.loader.exec_module(route)
with tarfile.open(out / 'k173-source-private.tar.gz') as archive:
    fixture = json.load(archive.extractfile('k173-source/validation.json'))['controls']
# Both extra AIF slot controls were read from the same boot before any changes.
fixture.update({route.TX[n]:{'value':'off','items':[]} for n in [0,7]})
protected = ['Headphone Jack Switch','Handset Mic Switch','Left Speaker Switch','Right Speaker Switch',
             'HPHL Volume','HPHR Volume','ADC2 Volume','RX HPH Mode']

class Hardware:
    def __init__(self, fail=None):
        self.state = copy.deepcopy(fixture); self.calls = []; self.fail = fail
    def read(self, name):
        return copy.deepcopy(self.state[name])
    def write(self, name, value):
        assert name not in protected, name
        self.calls.append((name,value)); self.state[name]['value'] = str(value)
        assert sum(route.number(self.state[n], self.state[n]['value']) for n in route.PLAY) <= 1
        if route.number(self.state[route.CAP],self.state[route.CAP]['value']):
            assert sum(route.number(self.state[n],self.state[n]['value']) for n in route.TX.values()) == 1
        if len(self.calls) == self.fail: raise OSError('injected failure after control commit')

cases = [('speaker',False,False),('headphones',False,False),('mic',False,False),('headset',False,False),
         ('init',False,False),('init',True,False),('init',True,True),('off',False,False)]
faults = 0
for mode, hp, mic in cases:
    h = Hardware(); plan = route.route_plan(mode,hp,mic); route.apply(h,plan)
    assert {n:h.state[n] for n in protected} == {n:fixture[n] for n in protected}
    end = copy.deepcopy(h.state); writes = len(h.calls)
    route.apply(h,plan)
    assert len(h.calls) == writes and h.state == end, 'repeat must avoid stream restart'
    for fail in range(1,writes+1):
        h = Hardware(fail)
        try: route.apply(h,plan)
        except OSError: pass
        else: raise AssertionError('missing injected failure')
        for n in h.state:
            assert route.number(h.state[n],h.state[n]['value']) == route.number(fixture[n],fixture[n]['value']), (mode,fail,n)
        faults += 1
h = Hardware()
try: route.apply(h,[('SLIM RX0 MUX','INVALID_AIF')])
except ValueError: pass
else: raise AssertionError('bad enum accepted')
assert not h.calls
oracle_rejections = 0
for name in [route.PLAY[1], route.TX[1]]:
    h = Hardware()
    try: h.write(name,1)
    except AssertionError: oracle_rejections += 1
assert oracle_rejections == 2
report = dict(stage=173, actual_helper_imported=True, helper_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
              route_cases=len(cases), post_commit_error_injections=faults, repeated_routes_do_not_write=True,
              rollback_restores_route=True, single_play_backend_and_single_mono_tx_invariants=True,
              bad_enum_rejected_before_mutation=True, oracle_negative_controls=oracle_rejections,
              jack_pins_and_analog_gain_and_classh_mode_untouched=True, physical_headset_not_tested=True, all_passed=True)
for folder in [ref,out]: (folder / 'host-tests-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)

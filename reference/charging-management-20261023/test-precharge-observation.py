"""Control/cleanup failure cases for the bounded observer; no device access."""
from pathlib import Path
import importlib.util
import json

spec = importlib.util.spec_from_file_location('precharge_observer',
        Path(__file__).with_name('precharge-observation.py'))
observer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)


class IO:
    def __init__(self, case):
        self.case = case
        self.mode = 'auto'
        self.t = 0
        self.actions = []
        self.recharge_reads = 0

    def now(self):
        return self.t

    def sleep(self, seconds):
        assert seconds >= 0
        self.t += seconds

    def record(self, phase, value):
        pass

    def cancelled(self):
        return self.case == 'cancel'

    def observe(self):
        voltage, current, phase = 4320000, 0, 0
        if self.mode == 'inhibit-charge':
            voltage = 3300000 if self.case not in ('deadline', 'no_discharge', 'cancel') else 4200000
            current = 0 if self.case == 'no_discharge' else -100000
        elif self.actions and self.actions[-1] == 'resume':
            self.recharge_reads += 1
            voltage, current = 3350000, 100000
            phase = 1 if self.recharge_reads <= 4 else 2
            if self.case == 'no_precharge':
                phase = 2
            if self.case == 'no_cc':
                phase = 1
        return dict(behaviour=self.mode, register08=8 if self.mode == 'inhibit-charge' else 0x10,
                    register13=phase << 2,
                    sample=dict(cell1_uv=voltage,
                                cell2_uv=voltage + (40000 if self.case == 'imbalance' and self.actions else 0),
                                temp_decic=240, logical_full=1, full_holding=1,
                                full_cause=3, session_seconds=0, desired_enable=1,
                                gauge_current_ua=current))

    def validate(self, value):
        if self.case == 'fault' and self.mode == 'inhibit-charge':
            raise RuntimeError('simulated health fault')
        if self.case == 'bad_before' and not self.actions:
            raise RuntimeError('invalid initial state')

    def command(self, action):
        self.actions.append(action)
        if self.case != 'stop_not_applied' or action != 'stop':
            self.mode = 'inhibit-charge' if action == 'stop' else 'auto'
        if self.case == 'lost_stop_ack' and action == 'stop':
            raise OSError('lost stop ACK after actual apply')
        if self.case == 'lost_resume_ack' and action == 'resume':
            raise OSError('lost resume ACK after actual apply')


class MidRangeIO(IO):
    def __init__(self, case):
        super().__init__(case)
        self.stop_reads = 0

    def observe(self):
        value = super().observe()
        s = value['sample']
        s.update(logical_full=0, full_holding=0, full_cause=0, session_seconds=42)
        if self.mode == 'inhibit-charge':
            self.stop_reads += 1
            s.update(cell1_uv=3500000 if self.stop_reads == 1 else 3300000,
                     cell2_uv=3500000 if self.stop_reads == 1 else 3300000,
                     session_seconds=43)
            if self.case == 'counter_jump' and self.stop_reads > 1:
                s['session_seconds'] = 44
            if self.case == 'counter_reset':
                s['session_seconds'] = 41
        elif not self.actions and self.case == 'not_enabled':
            s['desired_enable'] = 0
        return value


def main():
    results = []
    for case in ['success', 'lost_stop_ack', 'lost_resume_ack', 'fault', 'imbalance',
                 'deadline', 'no_discharge', 'cancel', 'stop_not_applied',
                 'no_precharge', 'no_cc', 'bad_before']:
        io = IO(case)
        result = observer.observe_precharge(io, 400 if case == 'no_discharge' else 20, 10)
        assert result['passed'] == (case == 'success'), (case, result)
        assert io.mode == 'auto' and io.actions.count('resume') <= 1, (case, result, io.actions)
        if case != 'bad_before':
            assert result['auto_restored'], (case, result)
        if case in ('lost_stop_ack', 'lost_resume_ack', 'fault', 'imbalance', 'stop_not_applied', 'bad_before'):
            assert result['error'] is not None, (case, result)
        assert not result['charge_parameters_changed'] and not result['physical_detach_tested']
        results.append(dict(case=case, passed=True, actions=io.actions, reason=result['reason']))
    for case in ['mid_success', 'counter_jump', 'counter_reset', 'not_enabled', 'default_full_refusal']:
        io = MidRangeIO(case)
        kwargs = {} if case == 'default_full_refusal' else dict(full_start_required=False)
        result = observer.observe_precharge(io, 20, 10, **kwargs)
        assert result['passed'] == (case == 'mid_success'), (case, result)
        assert io.mode == 'auto' and io.actions.count('resume') <= 1
        if case == 'mid_success':
            assert result['initial_session_seconds'] == 42 and result['stopped_session_seconds'] == 43
            assert result['initial_logical_full'] == 0 and io.t >= 5
        elif case in ['not_enabled', 'default_full_refusal']:
            assert io.actions == [] and result['error'] is not None
        else:
            assert result['auto_restored'] and result['error'] is not None
        results.append(dict(case=case, passed=True, actions=io.actions, reason=result['reason']))
    print(json.dumps(dict(passed=True, cases=results, hardware_access=False)))


if __name__ == '__main__':
    main()

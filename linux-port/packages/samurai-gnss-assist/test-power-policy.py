#!/usr/bin/python3
"""Exercise the production controller with a deterministic modem API."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('assist', Path(__file__).with_name('samurai-gnss-assist.py'))
assist = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assist)


class Modem:
    def __init__(self, power=1, active=True, mode='shutting-down'):
        self.value = dict(generation=('owner-a', 'modem-a'), state=-1, failure=2,
                          sim_absent=True, power=power, enabled=4 if active else 0)
        self.mode = mode
        self.calls = []
        self.mode_reads = 0
        self.on_set = None
        self.on_mode = None

    def read(self):
        return dict(self.value)

    def set(self, target):
        self.calls.append(target)
        if self.on_set:
            self.on_set(target)
        self.value['power'] = target
        return self.read()

    def get_mode(self):
        self.mode_reads += 1
        if self.on_mode:
            self.on_mode()
        return self.mode

    def update(self, policy):
        policy.update(self.read, self.set, self.get_mode)


class PowerPolicy(unittest.TestCase):
    def policy(self):
        return assist.GnssPowerPolicy(True)

    def test_initial_and_idle_low_power(self):
        p = self.policy(); m = Modem(); m.update(p)
        self.assertEqual(m.calls, [3]); self.assertTrue(p.owned)
        m.value['enabled'] = 0; m.update(p)
        self.assertEqual(m.calls, [3, 2]); self.assertFalse(p.owned)
        m.value['enabled'] = 4; m.update(p)
        self.assertEqual(m.calls, [3, 2, 3])
        self.assertEqual(m.mode_reads, 1)

    def test_idle_is_untouched(self):
        p = self.policy(); m = Modem(active=False); m.update(p)
        self.assertEqual(m.calls, []); self.assertEqual(m.mode_reads, 0)

    def test_preexisting_online_is_not_owned(self):
        p = self.policy(); m = Modem(power=3); m.update(p)
        m.value['enabled'] = 0; m.update(p)
        self.assertEqual(m.calls, []); self.assertFalse(p.owned)

    def test_explicit_offline_is_preserved(self):
        p = self.policy(); m = Modem(mode='offline')
        for _ in range(8): m.update(p)
        self.assertEqual(m.calls, []); self.assertEqual(m.mode_reads, 1)
        self.assertEqual(p.state['last_result'], 'offline-preserved')

    def test_other_device_sim_and_modem_state(self):
        for change in [{'state': 3}, {'failure': 3}, {'sim_absent': False}]:
            p = self.policy(); m = Modem(); m.value.update(change); m.update(p)
            self.assertEqual(m.calls, [])
        m = Modem(); m.update(assist.GnssPowerPolicy(False)); self.assertEqual(m.calls, [])

    def test_owner_replaced_during_mode_query(self):
        p = self.policy(); m = Modem()
        m.on_mode = lambda: m.value.update(generation=('owner-b', 'modem-b'))
        m.update(p); self.assertEqual(m.calls, [])

    def test_client_stopped_during_mode_query(self):
        p = self.policy(); m = Modem(); m.on_mode = lambda: m.value.update(enabled=0)
        m.update(p); self.assertEqual(m.calls, [])

    def test_client_stopped_during_online_request(self):
        p = self.policy(); m = Modem()
        m.on_set = lambda target: m.value.update(enabled=0) if target == 3 else None
        m.update(p); self.assertEqual(m.calls, [3, 2]); self.assertFalse(p.owned)

    def test_failed_request_is_not_repeated(self):
        p = self.policy(); m = Modem()
        def fail(_): raise TimeoutError('uncertain completion')
        m.on_set = fail
        for _ in range(8): m.update(p)
        m.value['enabled'] = 0; m.update(p)
        m.value['enabled'] = 4; m.update(p)
        self.assertEqual(m.calls, [3]); self.assertFalse(p.owned)

    def test_unconfirmed_completion_does_not_acquire_ownership(self):
        p = self.policy(); m = Modem()
        def replaced(_): m.value.update(generation=('owner-b', 'modem-b'))
        m.on_set = replaced; m.update(p)
        self.assertFalse(p.owned); self.assertEqual(m.calls, [3])

    def test_external_power_change_is_respected(self):
        p = self.policy(); m = Modem(); m.update(p)
        m.value['power'] = 2
        for _ in range(8): m.update(p)
        self.assertEqual(m.calls, [3]); self.assertFalse(p.owned)
        m.value['enabled'] = 0; m.update(p)
        m.value['enabled'] = 4; m.update(p)
        self.assertEqual(m.calls, [3, 3])

    def test_owner_restart_drops_stale_lease(self):
        p = self.policy(); m = Modem(); m.update(p)
        m.value.update(generation=('owner-b', 'modem-b'), enabled=0)
        m.update(p); self.assertEqual(m.calls, [3]); self.assertFalse(p.owned)

    def test_sim_appears_before_stop(self):
        p = self.policy(); m = Modem(); m.update(p)
        m.value.update(sim_absent=False, enabled=0); m.update(p)
        self.assertEqual(m.calls, [3]); self.assertFalse(p.owned)

    def test_failed_idle_release_never_sends_offline(self):
        p = self.policy(); m = Modem(); m.update(p); m.value['enabled'] = 0
        def fail(_): raise RuntimeError('rejected')
        m.on_set = fail
        for _ in range(8): m.update(p)
        self.assertEqual(m.calls, [3, 2]); self.assertTrue(p.owned)


if __name__ == '__main__':
    unittest.main(verbosity=2)

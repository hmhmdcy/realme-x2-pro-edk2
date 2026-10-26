"""Run the real helper against an in-memory tracefs model, never the device."""
from pathlib import Path
import builtins
import contextlib
import importlib.util
import io
import json
import os
import stat
import sys
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel459')
SOURCE = (HERE/'trace-instance.py').read_text()
spec = importlib.util.spec_from_file_location('trace459', HERE/'trace-instance.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


class Model:
    """Small tracefs semantics model: directory removal removes virtual controls."""
    def __init__(self, plan):
        self.plan = plan
        self.files, self.dirs, self.ids = {}, set(), {}
        self.log, self.locks, self.failures, self.links = [], set(), {}, set()
        self.next_inode = 100
        for root in ['/', '/sys', '/sys/kernel', '/sys/kernel/tracing', '/sys/kernel/tracing/instances',
                     '/private', '/private/kernel459']:
            self.add_dir(root)
        p = plan
        self.files.update({h.SYS_ONLINE: p.probe['online_cpus'].encode(), h.SYS_POSSIBLE: b'0-7',
                           h.BOOT_ID: b'fake-boot-id\n', '/proc/self/mountinfo':
                           b'39 1 0:30 / /sys/kernel/tracing rw - tracefs tracefs rw\n',
                           '/proc/interrupts': p.probe['interrupts'].encode(),
                           '/proc/cmdline': p.extra['cmdline'].encode(),
                           '/proc/meminfo': p.extra['meminfo'].encode(),
                           p.root+'/available_events': ('\n'.join(h.EVENTS)+'\n').encode()})
        for key, value in p.video.items():
            self.files['/sys/class/video4linux/'+p.node+'/'+key] = value.encode()
        self.controls(p.root, initial=False)
        self.files[p.root+'/trace_clock'] = p.probe['trace_clock'].encode()
        self.files[p.root+'/buffer_size_kb'] = p.extra['buffer_size_kb'].encode()
        self.files[p.root+'/buffer_total_size_kb'] = p.extra['buffer_total_size_kb'].encode()
        self.files[p.root+'/tracing_on'] = b'1'
        for name in p.probe['existing_instances']:
            self.add_dir(p.root+'/instances/'+name)
            self.controls(p.root+'/instances/'+name, initial=False)
        self.original = dict(self.files)

    def add_dir(self, path):
        self.dirs.add(path)
        self.ids[path] = [101, self.next_inode, 0, stat.S_IFDIR]
        self.next_inode += 1

    def controls(self, root, initial):
        for key, value in {'tracing_on':'0', 'current_tracer':'nop', 'trace_clock':'[local] mono boot',
                           'buffer_size_kb':'1410', 'buffer_total_size_kb':'11280', 'tracing_cpumask':'ff',
                           'options/overwrite':'1', 'events/enable':'0', 'set_event_pid':'',
                           'set_event_notrace_pid':'', 'trace':'# bounded trace\nrecord 1\nrecord 2\n'}.items():
            self.files[root+'/'+key] = value.encode()
        self.add_dir(root+'/events')
        for name in (*h.EVENTS, 'unused:do_not_enable'):
            group, event = name.split(':')
            for directory in [root+'/events/'+group, root+'/events/'+group+'/'+event]:
                if directory not in self.dirs:
                    self.add_dir(directory)
            self.files[root+'/events/'+group+'/enable'] = b'0'
            for key, value in {'enable':b'0', 'filter':b'none',
                               'format':self.plan.probe['formats'].get(name, '').encode()}.items():
                self.files[root+'/events/'+group+'/'+event+'/'+key] = value
        if initial:
            self.add_dir(root+'/per_cpu')
            for number in range(8):
                self.add_dir(root+f'/per_cpu/cpu{number}')
                self.files[root+f'/per_cpu/cpu{number}/stats'] = b'entries: 2\noverrun: 0\ncommit overrun: 0\ndropped events: 0\n'

    def failure(self, operation, path):
        key = (operation, path)
        if self.failures.get(key, 0):
            self.failures[key] -= 1
            raise OSError('injected '+operation+' failure')

    def no_links(self, path):
        h.safe_absolute(path)
        h.require(not any(path == link or path.startswith(link+'/') for link in self.links), 'model symlink refused')

    def read(self, path, maximum=2*1024*1024):
        self.failure('read', path)
        value = self.files[path]
        h.require(len(value) <= maximum, 'bounded read exceeded')
        return value

    def write(self, path, value):
        self.no_links(path)
        h.require(path.startswith(self.plan.instance+'/'), 'model caught global/unrelated write')
        self.failure('write', path)
        self.log.append(('write', path, value))
        if path.endswith('/events/enable'):
            for key in list(self.files):
                if key.startswith(self.plan.instance+'/events/') and key.endswith('/enable'):
                    self.files[key] = value
        elif path.endswith('/trace_clock'):
            value = ('local ['+value.decode()+'] boot').encode()
        elif path.endswith('/buffer_size_kb'):
            value = str(int(value)+1).encode()  # 512 request -> 513 reported after page rounding
            self.files[self.plan.instance+'/buffer_total_size_kb'] = str(int(value)*8).encode()
        self.files[path] = value

    def exists(self, path):
        return path in self.dirs or path in self.files or path in self.links

    def identity(self, path):
        self.no_links(path)
        return self.ids[path]

    def mkdir(self, path):
        self.no_links(path)
        h.require(path == self.plan.instance or path == '/private/kernel459/'+self.plan.name, 'mkdir outside task')
        self.failure('mkdir', path)
        if self.exists(path):
            raise FileExistsError(path)
        self.log.append(('mkdir', path))
        self.add_dir(path)
        if path == self.plan.instance:
            self.controls(path, initial=True)

    def rmdir(self, path):
        self.no_links(path)
        h.require(path == self.plan.instance, 'model caught non-task removal')
        self.failure('rmdir', path)
        self.log.append(('rmdir', path))
        for key in list(self.files):
            if key.startswith(path+'/'):
                del self.files[key]
        for key in list(self.dirs):
            if key == path or key.startswith(path+'/'):
                self.dirs.remove(key)
                del self.ids[key]

    def children(self, path):
        h.require(path in self.dirs, 'not a model directory')
        prefix = path+'/'
        return sorted({item[len(prefix):].split('/')[0] for item in self.dirs | set(self.files)
                       if item.startswith(prefix) and item[len(prefix):]})

    def private_parent(self, path):
        self.no_links(path)
        h.require(path in self.dirs, 'missing private directory')

    def replace_private(self, path, value):
        h.require(path.startswith('/private/kernel459/'+self.plan.name+'/'), 'private write escaped')
        self.failure('save', path)
        self.files[path] = value

    def lock(self, path):
        h.require(path not in self.locks, 'concurrent controller refused')
        self.locks.add(path)
        return path

    def unlock(self, path, handle):
        h.require(path == handle and path in self.locks, 'invalid unlock')
        self.locks.remove(path)

    def copy(self, source, destination, maximum):
        h.require(self.files[self.plan.instance+'/tracing_on'] == b'0', 'read before instance stopped')
        h.require(source == self.plan.instance+'/trace' and destination not in self.files, 'copy boundary')
        self.log.append(('copy', source, destination))
        if self.failures.get(('copy', source), 0):
            self.files[destination] = b'partial-private-evidence'
            self.failure('copy', source)
        value = self.files[source]
        h.require(len(value) <= maximum, 'trace export cap')
        self.files[destination] = value
        return dict(bytes=len(value), sha256=h.digest(value), eof=True)

    def unchanged_unrelated(self):
        return all(self.files.get(key) == value for key, value in self.original.items())


def rejected(call):
    try:
        call()
    except (h.Rejected, OSError, KeyError):
        return
    raise AssertionError('rejection was required')


def main():
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    probe = (PRIVATE.parent/'kernel457/trace-capabilities-private.json').read_bytes()
    extra = (PRIVATE.parent/'kernel457/trace-extra-private.json').read_bytes()
    selection = dict(schema='samurai-k459-trace-selection-v1', probe_sha256=h.digest(probe), extra_sha256=h.digest(extra),
                     tracefs='/sys/kernel/tracing', clock='mono', instance='k459-host-review',
                     ownership_token='a'*32, full_video_node='video0', full_minor=0,
                     vfe_irq=225, vfe_irq_action='acb3000.camss_msm_vfe0')
    selected = h.packed(selection)
    plan = h.Plan(probe, selected, extra)
    evidence = '/private/kernel459/'+plan.name
    cases = []

    def case(name, function):
        function()
        cases.append(dict(name=name, passed=True))

    def lifecycle():
        fs = Model(plan)
        session = h.Session(plan, fs, evidence)
        started = session.start()
        assert started['phase'] == 'started' and started['initial_main_ring_total_kib'] == 11280
        assert session.config()['buffer_total_size_kb'] == '4104'
        assert fs.files[plan.root+'/tracing_on'] == b'1'
        assert b'[local]' in fs.files[plan.root+'/trace_clock']
        captured = h.Session(plan, fs, evidence).stop_read()
        assert captured['phase'] == 'captured' and len(captured['capture_attempts'][-1]['stats']) == 8
        cleaned = h.Session(plan, fs, evidence).cleanup()
        assert cleaned['phase'] == 'cleaned' and not fs.exists(plan.instance)
        assert fs.unchanged_unrelated() and not fs.locks
        assert all(item[1].startswith(plan.instance+'/') for item in fs.log if item[0] == 'write')
        assert list(h.Session(plan, fs, evidence).plan.filters) == list(h.EVENTS)
        (PRIVATE/'model-lifecycle-private.json').write_bytes(h.packed(cleaned))
    case('start_page_rounded_11280kib_then_4104kib_stop_full_read_stats_cleanup_global_and_display_radio_preserved', lifecycle)

    def collision():
        fs = Model(plan)
        fs.add_dir(plan.instance)
        rejected(lambda: h.Session(plan, fs, evidence).start())
        assert not fs.log and fs.exists(plan.instance)
    case('existing_instance_rejected_without_writes', collision)

    def rollback(fail_cleanup=False):
        fs = Model(plan)
        fs.failures['write', plan.event_path(h.EVENTS[2], 'filter')] = 1
        if fail_cleanup:
            fs.failures['rmdir', plan.instance] = 1
        session = h.Session(plan, fs, evidence)
        rejected(session.start)
        state = json.loads(fs.files[session.state_path])
        assert state['phase'] == 'start_failed' and state['errors']
        assert state['rollback_removed_instance'] is not fail_cleanup
        assert fs.exists(plan.instance) is fail_cleanup and fs.unchanged_unrelated()
        if fail_cleanup:
            assert [item['operation'] for item in state['errors']] == ['start', 'rollback']
            assert fs.files[plan.instance+'/tracing_on'] == b'0'
    case('partial_start_rolls_back_only_owned_instance_with_failure_receipt', rollback)
    case('rollback_failure_is_retained_and_not_swallowed', lambda: rollback(True))

    def capture_retry():
        fs = Model(plan)
        session = h.Session(plan, fs, evidence)
        session.start()
        fs.failures['copy', plan.instance+'/trace'] = 1
        rejected(session.stop_read)
        assert fs.files[plan.instance+'/tracing_on'] == b'0' and fs.exists(plan.instance)
        assert json.loads(fs.files[session.state_path])['phase'] == 'capture_failed'
        rejected(session.cleanup)
        # cleanup rejection must not make a partial capture eligible for deletion.
        assert fs.exists(plan.instance)
        assert json.loads(fs.files[session.state_path])['phase'] == 'capture_failed'
        assert session.stop_read()['phase'] == 'captured'
    case('partial_export_retains_stopped_instance_and_evidence_cleanup_refused', capture_retry)

    def full_retry():
        fs = Model(plan)
        session = h.Session(plan, fs, evidence)
        session.start()
        fs.failures['copy', plan.instance+'/trace'] = 1
        rejected(session.stop_read)
        captured = session.stop_read()
        assert len(captured['capture_attempts']) == 2 and not captured['capture_attempts'][0]['complete']
        assert captured['capture_attempts'][1]['complete']
        session.cleanup()
    case('capture_retry_keeps_partial_and_uses_new_complete_export', full_retry)

    def drift():
        fs = Model(plan)
        session = h.Session(plan, fs, evidence)
        session.start()
        fs.files[plan.event_path(h.EVENTS[0], 'filter')] = b'type == 10'
        rejected(session.stop_read)
        assert fs.exists(plan.instance) and fs.files[plan.instance+'/tracing_on'] == b'1'
        assert fs.unchanged_unrelated()
    case('configuration_drift_refuses_control_and_leaves_explicit_failure', drift)

    def replaced():
        fs = Model(plan)
        session = h.Session(plan, fs, evidence)
        session.start()
        fs.ids[plan.instance][1] += 100
        count = len(fs.log)
        rejected(session.stop_read)
        assert len(fs.log) == count and fs.exists(plan.instance)
    case('replaced_instance_identity_rejected', replaced)

    def cleanup_error():
        fs = Model(plan)
        session = h.Session(plan, fs, evidence)
        session.start(); session.stop_read()
        fs.failures['rmdir', plan.instance] = 1
        rejected(session.cleanup)
        assert json.loads(fs.files[session.state_path])['phase'] == 'cleanup_failed'
        assert fs.exists(plan.instance)
        assert session.cleanup()['phase'] == 'cleaned'
    case('cleanup_failure_is_visible_and_retryable', cleanup_error)

    for field, value in [('instance', 'display'), ('instance', '../radio'), ('tracefs', '/sys/kernel'),
                         ('full_minor', 6), ('vfe_irq', 1), ('vfe_irq_action', 'guessed_vfe')]:
        changed = dict(selection, **{field:value})
        case('reject_bad_selection_'+field+'_'+str(value).replace('/', '_'),
             lambda changed=changed: rejected(lambda: h.Plan(probe, h.packed(changed), extra)))
    case('reject_kernel_evidence_path', lambda: rejected(lambda: h.Session(plan, Model(plan), '/sys/'+plan.name)))

    for name, path, value in [('online_changed', h.SYS_ONLINE, b'0-3'),
                              ('possible_exceeds_creation_limit', h.SYS_POSSIBLE, b'0-15'),
                              ('possible_exceeds_steady_limit', h.SYS_POSSIBLE, b'0-16'),
                              ('low_memory', '/proc/meminfo', b'MemAvailable: 524287 kB\n'),
                              ('cmdline_changed', '/proc/cmdline', b'trace_buf_size=32M')]:
        def boundary(path=path, value=value):
            fs = Model(plan)
            fs.files[path] = value
            rejected(lambda: h.Session(plan, fs, evidence).start())
            assert not fs.log
        case('reject_'+name+'_before_mkdir', boundary)

    def symlink():
        fs = Model(plan)
        fs.links.add(plan.root)
        rejected(lambda: h.Session(plan, fs, evidence).start())
        assert not fs.log
    case('reject_symlink_tracefs_root', symlink)

    def inert_import():
        def fail(*args, **kwargs):
            raise AssertionError('I/O at import')
        with patch.object(builtins, 'open', fail), patch.object(os, 'open', fail), patch.object(os, 'stat', fail), patch.object(os, 'listdir', fail):
            exec(compile(SOURCE, 'trace-instance-inert-import', 'exec'), {'__name__':'inert_import'})
    case('real_module_import_performs_no_file_io', inert_import)

    # The default CLI uses only supplied private input files; every tracefs method is forbidden.
    (PRIVATE/'selection-private.json').write_bytes(selected)
    def default_render():
        args = ['trace-instance.py', '--probe', str(PRIVATE.parent/'kernel457/trace-capabilities-private.json'),
                '--extra', str(PRIVATE.parent/'kernel457/trace-extra-private.json'),
                '--selection', str(PRIVATE/'selection-private.json'), '--evidence-dir', evidence]
        def fail(*args, **kwargs):
            raise AssertionError('tracefs I/O in default render')
        output = io.StringIO()
        with patch.object(sys, 'argv', args), contextlib.redirect_stdout(output), \
             patch.object(h.RealFiles, 'read', fail), patch.object(h.RealFiles, 'write', fail), \
             patch.object(h.RealFiles, 'mkdir', fail), patch.object(h.RealFiles, 'rmdir', fail):
            h.main()
        rendered = json.loads(output.getvalue())
        assert rendered['rendered'] and not rendered['executed'] and not rendered['pid_filter_used']
        (HERE/'render-validation.json').write_bytes(h.packed(rendered))
    case('default_cli_only_renders_bound_actual_probe_without_tracefs_io', default_render)

    assert h.default_buffer_bytes('x=1') == 1441792
    assert h.default_buffer_bytes('trace_buf_size=1M') == 1048576
    assert h.buffer_sizes('7 (expanded: 1408)') == (7, 1408)
    report = dict(stage=459, helper_sha256=h.digest(SOURCE.encode()), cases=cases,
                  actual457_probe_sha256=h.digest(probe), actual457_extra_sha256=h.digest(extra),
                  actual_probe_used_only_as_offline_input=True, simulated_initial_ring_kib=11280,
                  simulated_steady_reported_ring_kib=4104, requested_total_ring_kib=4096,
                  per_cpu_requested_kib=512, steady_limit_kib=8192,
                  creation_limit_kib=16384, required_mem_available_kib=524288,
                  no_real_tracefs_access=True, no_phone_sdk_compile=True,
                  host_model_does_not_prove_tracefs_hardware_behavior=True, passed=True)
    (HERE/'helper-validation.json').write_bytes(h.packed(report))
    print(json.dumps(dict(stage=459, cases=len(cases), passed=True, no_real_tracefs_access=True)))


if __name__ == '__main__':
    main()

"""A small trace-instance lifecycle, not a camera/handoff transaction.

Import is inert. The CLI renders by default. Real tracefs I/O needs --execute.
No transport, process signalling, mounting, SDK or kernel build is included.
"""
from pathlib import PurePosixPath, Path
import argparse
import hashlib
import json
import os
import re
import shlex
import stat

EVENTS = (
    'vb2:vb2_qbuf', 'vb2:vb2_buf_queue', 'vb2:vb2_buf_done', 'vb2:vb2_dqbuf',
    'v4l2:v4l2_qbuf', 'v4l2:v4l2_dqbuf',
    'irq:irq_handler_entry', 'irq:irq_handler_exit',
)
ROOTS = ('/sys/kernel/tracing', '/sys/kernel/debug/tracing')
PER_CPU_KIB = 512
ROUNDING_KIB = 4  # original363 uses 4KiB pages; ring data capacity rounds upward
TOTAL_KIB = 8192
CREATE_LIMIT_KIB = 16384
MIN_AVAILABLE_KIB = 512 * 1024
KERNEL_DEFAULT_BYTES = 1441792
EXPORT_MAX_BYTES = 128 * 1024 * 1024
SYS_ONLINE = '/sys/devices/system/cpu/online'
SYS_POSSIBLE = '/sys/devices/system/cpu/possible'
BOOT_ID = '/proc/sys/kernel/random/boot_id'


class Rejected(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise Rejected(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def packed(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def safe_absolute(value):
    require(isinstance(value, str) and '\x00' not in value, 'unsafe path')
    require(value.startswith('/') and not value.endswith('/'), 'absolute normalized path required')
    require(all(part not in ('', '.', '..') for part in value.split('/')[1:]), 'unsafe path components')
    require(str(PurePosixPath(value)) == value, 'non-canonical path')
    return value


def cpus(text):
    require(isinstance(text, str) and re.fullmatch(r'\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*', text.strip()), 'invalid CPU list')
    result = set()
    for part in text.strip().split(','):
        bounds = list(map(int, part.split('-')))
        low, high = (bounds[0], bounds[-1])
        require(0 <= low <= high < 4096 and high - low < 4096, 'invalid CPU range')
        group = set(range(low, high + 1))
        require(not result.intersection(group), 'duplicate CPU')
        result.update(group)
    require(0 < len(result) <= TOTAL_KIB // PER_CPU_KIB, 'online/possible CPUs exceed 8MiB budget')
    return sorted(result)


def cpu_mask(numbers):
    value = sum(1 << number for number in numbers)
    words = []
    while value:
        words.append(f'{value & 0xffffffff:08x}')
        value >>= 32
    return ','.join(reversed(words)).lstrip('0') or '0'


def mask_value(text):
    require(re.fullmatch(r'[0-9a-fA-F]+(?:,[0-9a-fA-F]{1,8})*', text.strip()), 'invalid CPU mask')
    return int(text.replace(',', '').strip(), 16)


def format_fields(text):
    fields = set()
    for declaration in re.findall(r'field:([^;]+);\s*offset:\s*\d+;', text):
        match = re.search(r'([A-Za-z_]\w*)(?:\[[^\]]*\])?\s*$', declaration)
        require(match is not None, 'unsupported event field declaration')
        fields.add(match.group(1))
    return fields


def irq_line(text, number, action):
    rows = [line for line in text.splitlines() if re.match(rf'^\s*{number}:', line)]
    return len(rows) == 1 and re.search(r'(?:^|[,\s])' + re.escape(action) + r'(?:$|[,\s])', rows[0]) is not None


def available_memory(meminfo):
    values = re.findall(r'^MemAvailable:\s+(\d+) kB$', meminfo, re.MULTILINE)
    require(len(values) == 1 and int(values[0]) >= MIN_AVAILABLE_KIB, 'MemAvailable below 512MiB or unavailable')
    return int(values[0])


def default_buffer_bytes(cmdline):
    values = [word.split('=', 1)[1] for word in shlex.split(cmdline) if word.startswith('trace_buf_size=')]
    if not values:
        return KERNEL_DEFAULT_BYTES
    match = re.fullmatch(r'(\d+)([KMG]?)', values[-1], re.IGNORECASE)
    require(match is not None, 'unsupported trace_buf_size boot argument')
    return max(4096, int(match[1]) * 1024 ** ('KMG'.find(match[2].upper()) + 1 if match[2] else 0))


def buffer_sizes(text):
    match = re.fullmatch(r'(\d+)(?: \(expanded: (\d+)\))?', text.strip())
    require(match is not None, 'unsupported buffer size report')
    return int(match[1]), int(match[2]) if match[2] else None


class Plan:
    """Pure validation of a collected 457 probe and an explicit node/IRQ selection."""
    def __init__(self, probe_bytes, selection_bytes, extra_bytes):
        self.probe = json.loads(probe_bytes)
        self.selection = json.loads(selection_bytes)
        p, s = self.probe, self.selection
        require(s.get('schema') == 'samurai-k459-trace-selection-v1', 'selection schema')
        require(s.get('probe_sha256') == digest(probe_bytes), 'selection is not bound to this probe')
        require(s.get('extra_sha256') == digest(extra_bytes), 'selection is not bound to capacity supplement')
        self.extra = json.loads(extra_bytes)
        require(self.extra.get('phone_changed') is False, 'capacity supplement was not read-only')
        self.root = safe_absolute(p['tracefs'])
        require(self.root in ROOTS, 'unapproved tracefs root')
        require(s.get('tracefs') == self.root and s.get('clock') == 'mono', 'explicit tracefs/mono selection required')
        require('mono' in p['trace_clock'].replace('[', '').replace(']', '').split(), 'mono absent from actual probe')
        require(p.get('instances_supported') is True, 'instances not reported')
        require(p.get('phone_changed') is False, 'not a read-only 457 probe')
        require(p.get('charging_before') == p.get('charging_after'), 'probe charging changed')
        self.name = s['instance']
        require(re.fullmatch(r'k459-[a-z0-9][a-z0-9-]{0,42}', self.name), 'unsafe task instance name')
        require(self.name not in p['existing_instances'], 'instance existed at probe time')
        self.token = s['ownership_token']
        require(re.fullmatch(r'[0-9a-f]{32}', self.token), 'explicit ownership token required')
        self.instance = self.root + '/instances/' + self.name
        self.online = cpus(p['online_cpus'])
        require(cpus(self.extra['online_cpus']) == self.online, 'capacity/probe CPU lists differ')
        self.default_bytes = default_buffer_bytes(self.extra['cmdline'])
        self.mem_available_kib = available_memory(self.extra['meminfo'])
        _, expanded = buffer_sizes(self.extra['buffer_size_kb'])
        _, total_expanded = buffer_sizes(self.extra['buffer_total_size_kb'])
        require(expanded == self.default_bytes // 1024 and total_expanded == expanded * len(self.online),
                'expanded capacity is not consistent with boot argument/fixed kernel default')
        require(self.default_bytes * len(self.online) <= CREATE_LIMIT_KIB * 1024, 'default creation ring exceeds 16MiB')
        self.minor, self.irq = s['full_minor'], s['vfe_irq']
        require(type(self.minor) is int and 0 <= self.minor < 1 << 20, 'invalid FULL minor')
        require(type(self.irq) is int and 0 < self.irq < 1 << 31, 'invalid VFE IRQ')
        self.node, self.action = s['full_video_node'], s['vfe_irq_action']
        require(re.fullmatch(r'video\d+', self.node), 'explicit video node required')
        require(re.fullmatch(r'[A-Za-z0-9_.:-]+', self.action), 'unsafe IRQ action name')
        require(self.node in p['video_nodes'], 'node absent from actual probe')
        self.video = p['video_nodes'][self.node]
        require(re.fullmatch(r'\d+:\d+', self.video['dev']), 'invalid probed device number')
        require(int(self.video['dev'].split(':')[1]) == self.minor, 'minor does not match selected probed node')
        require(irq_line(p['interrupts'], self.irq, self.action), 'IRQ/action not in actual probe')
        for name in EVENTS:
            require(p['wanted_events'].get(name) is True and name in p['formats'], 'required event absent: ' + name)
            fields = format_fields(p['formats'][name])
            required = {'common_pid'}
            if name.startswith('vb2:'):
                required |= {'owner', 'index', 'type', 'queued_count', 'owned_by_drv_count', 'timestamp'}
            elif name.startswith('v4l2:'):
                required |= {'minor', 'index', 'type', 'sequence', 'flags', 'timestamp'}
            else:
                required |= {'irq', 'name' if name.endswith('_entry') else 'ret'}
            require(required <= fields, 'actual format missing fields: ' + name)
        self.filters = {name: ('type == 9' if name.startswith('vb2:') else
                              f'minor == {self.minor}' if name.startswith('v4l2:') else
                              f'irq == {self.irq}') for name in EVENTS}
        self.probe_bytes, self.selection_bytes = probe_bytes, selection_bytes
        self.key = digest(packed(dict(probe_sha256=digest(probe_bytes), selection_sha256=digest(selection_bytes),
                                     extra_sha256=digest(extra_bytes))))

    def event_path(self, name, leaf):
        require(name in EVENTS and leaf in ('format', 'filter', 'enable'), 'event path outside contract')
        return self.instance + '/events/' + name.replace(':', '/') + '/' + leaf

    def render(self, action, evidence):
        return dict(schema='samurai-k459-trace-plan-v1', rendered=True, executed=False,
                    action=action, instance=self.instance, evidence_dir=evidence,
                    clock='mono', per_cpu_kib=PER_CPU_KIB, total_limit_kib=TOTAL_KIB,
                    creation_ring_limit_kib=CREATE_LIMIT_KIB,
                    probed_creation_ring_kib=self.default_bytes * len(self.online) // 1024,
                    minimum_available_memory_kib=MIN_AVAILABLE_KIB,
                    probed_online_cpu_count=len(self.online), filters=self.filters,
                    pid_filter_used=False, trace_export_max_bytes=EXPORT_MAX_BYTES,
                    runtime_checks=['fresh caller-owned camera handoff outside this helper',
                                    'root, tracefs mount, current online/possible CPUs, probe formats/node/IRQ',
                                    'new instance only; actual total allocation <=8192KiB',
                                    'identity and complete owned configuration match before stop/delete'],
                    camera_transaction_included=False, transport_included=False)


class RealFiles:
    """Injectable file interface. Instantiation itself does no I/O."""
    def read(self, path, maximum=2 * 1024 * 1024):
        with open(path, 'rb') as stream:
            value = stream.read(maximum + 1)
        require(len(value) <= maximum, 'bounded read exceeded: ' + path)
        return value

    def write(self, path, value):
        self.no_links(path)
        with open(path, 'wb', buffering=0) as stream:
            require(stream.write(value) == len(value), 'short write: ' + path)

    def exists(self, path):
        return os.path.lexists(path)

    def no_links(self, path):
        safe_absolute(path)
        current = Path('/')
        for component in PurePosixPath(path).parts[1:]:
            current /= component
            require(not current.is_symlink(), 'symlink path refused: ' + str(current))

    def identity(self, path):
        self.no_links(path)
        value = os.stat(path, follow_symlinks=False)
        return [value.st_dev, value.st_ino, value.st_uid, stat.S_IFMT(value.st_mode)]

    def mkdir(self, path):
        self.no_links(path)
        os.mkdir(path, 0o700)

    def rmdir(self, path):
        self.no_links(path)
        os.rmdir(path)

    def children(self, path):
        return sorted(os.listdir(path))

    def private_parent(self, path):
        self.no_links(path)
        value = os.stat(path)
        require(stat.S_ISDIR(value.st_mode) and value.st_uid == os.geteuid() and not value.st_mode & 0o022,
                'evidence parent must be owned and not group/world writable')

    def replace_private(self, path, value):
        self.no_links(path)
        temporary = path + '.pending'
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(value)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.lexists(temporary):
                os.unlink(temporary)

    def lock(self, path):
        self.no_links(path)
        return os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)

    def unlock(self, path, handle):
        os.close(handle)
        os.unlink(path)

    def copy(self, source, destination, maximum):
        self.no_links(destination)
        total, hasher = 0, hashlib.sha256()
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as target, open(source, 'rb') as stream:
            while True:
                block = stream.read(min(65536, maximum - total + 1))
                if not block:
                    break
                require(total + len(block) <= maximum, 'trace text export exceeded cap; partial evidence retained')
                target.write(block)
                total += len(block)
                hasher.update(block)
            target.flush()
            os.fsync(target.fileno())
        return dict(bytes=total, sha256=hasher.hexdigest(), eof=True)


class Session:
    def __init__(self, plan, files, evidence_dir):
        self.plan, self.fs = plan, files
        self.evidence = safe_absolute(evidence_dir)
        require(PurePosixPath(self.evidence).name == plan.name, 'evidence basename must equal task instance')
        require(not any(self.evidence == root or self.evidence.startswith(root + '/') for root in ('/sys', '/proc', '/dev')),
                'evidence must be outside kernel control filesystems')
        self.state_path = self.evidence + '/state.json'
        self.lock_path = self.evidence + '/controller.lock'
        self.state = None

    def text(self, path):
        return self.fs.read(path).decode().strip()

    def own_write(self, relative, value):
        require(relative in ('tracing_on', 'current_tracer', 'trace_clock', 'buffer_size_kb',
                             'tracing_cpumask', 'options/overwrite', 'events/enable', 'trace',
                             'set_event_pid', 'set_event_notrace_pid') or
                any(relative == 'events/' + name.replace(':', '/') + '/' + leaf
                    for name in EVENTS for leaf in ('enable', 'filter')),
                'write outside owned control allowlist')
        require(self.state is not None and self.state.get('instance_identity') == self.fs.identity(self.plan.instance),
                'instance ownership mismatch before write')
        self.fs.write(self.plan.instance + '/' + relative, value.encode())

    def save(self):
        self.fs.replace_private(self.state_path, packed(self.state))

    def globals(self):
        root = self.plan.root
        names = [name for name in self.fs.children(root + '/instances') if name != self.plan.name]
        fields = ('tracing_on', 'current_tracer', 'trace_clock', 'buffer_size_kb', 'tracing_cpumask', 'events/enable')
        return {base: {key: self.text(base + '/' + key) for key in fields}
                for base in [root] + [root + '/instances/' + name for name in names]}

    def runtime_preflight(self):
        p = self.plan
        self.fs.no_links(p.root)
        mounted = False
        for line in self.text('/proc/self/mountinfo').splitlines():
            head, separator, tail = line.partition(' - ')
            if separator and len(head.split()) >= 5 and head.split()[4] == p.root and tail.split()[0] == 'tracefs':
                mounted = True
        require(mounted, 'selected root is not an exact current tracefs mount; no mounting is attempted')
        require(cpus(self.text(SYS_ONLINE)) == p.online, 'online CPUs changed since probe')
        possible = cpus(self.text(SYS_POSSIBLE))
        require(set(p.online) <= set(possible), 'online CPUs outside possible list')
        require(len(possible) * PER_CPU_KIB <= TOTAL_KIB, 'possible CPUs exceed worst-case allocation budget')
        require(self.text('/proc/cmdline') == p.extra['cmdline'].strip(), 'cmdline changed since capacity supplement')
        require(default_buffer_bytes(self.text('/proc/cmdline')) == p.default_bytes, 'creation default changed')
        require(p.default_bytes * len(possible) <= CREATE_LIMIT_KIB * 1024, 'possible CPUs exceed creation ring budget')
        available_memory(self.text('/proc/meminfo'))
        _, expanded = buffer_sizes(self.text(p.root + '/buffer_size_kb'))
        require(expanded == p.default_bytes // 1024, 'current expanded default no longer agrees; do not treat 7KiB as instance default')
        require('mono' in self.text(p.root + '/trace_clock').replace('[', '').replace(']', '').split(), 'mono no longer available')
        available = set(self.text(p.root + '/available_events').split())
        require(set(EVENTS) <= available, 'events changed since probe')
        for name in EVENTS:
            require(self.fs.read(p.root + '/events/' + name.replace(':', '/') + '/format').decode() == p.probe['formats'][name],
                    'actual event format changed since probe: ' + name)
        video = '/sys/class/video4linux/' + p.node
        require(self.text(video + '/dev') == p.video['dev'] and self.text(video + '/name') == p.video['name'], 'selected node changed')
        require(irq_line(self.text('/proc/interrupts'), p.irq, p.action), 'selected IRQ/action changed')
        return possible

    def config(self):
        root = self.plan.instance
        fields = ('current_tracer', 'trace_clock', 'buffer_size_kb', 'buffer_total_size_kb',
                  'tracing_cpumask', 'options/overwrite', 'set_event_pid', 'set_event_notrace_pid')
        result = {key: self.text(root + '/' + key) for key in fields if self.fs.exists(root + '/' + key)}
        result['events'] = {}
        for subsystem in self.fs.children(root + '/events'):
            if not re.fullmatch(r'[A-Za-z0-9_]+', subsystem):
                continue
            directory = root + '/events/' + subsystem
            # The tracefs event root also has regular control files.
            if not self.fs.exists(directory + '/enable'):
                continue
            for event in self.fs.children(directory):
                enable = directory + '/' + event + '/enable'
                if re.fullmatch(r'[A-Za-z0-9_]+', event) and self.fs.exists(enable):
                    name = subsystem + ':' + event
                    enabled = self.text(enable)
                    if enabled != '0' or name in EVENTS:
                        result['events'][name] = dict(enable=enabled,
                            filter=self.text(directory + '/' + event + '/filter') if name in EVENTS else None)
        return result

    def check_config(self, config):
        require(config.get('current_tracer') == 'nop', 'unexpected tracer')
        require('[mono]' in config.get('trace_clock', '').split(), 'instance clock is not mono')
        require(PER_CPU_KIB <= int(config.get('buffer_size_kb', '-1')) < PER_CPU_KIB + ROUNDING_KIB,
                'per-CPU capacity exceeds one-page rounding of requested 512KiB')
        require(0 < int(config.get('buffer_total_size_kb', '-1')) <= TOTAL_KIB, 'actual total buffer exceeds bound')
        require(config.get('options/overwrite') == '1', 'tail overwrite mode required')
        require(mask_value(config.get('tracing_cpumask', '')) == sum(1 << number for number in self.plan.online), 'CPU mask mismatch')
        require(config.get('set_event_pid', '') in ('', 'no pid'), 'PID filter must not exclude IRQ context')
        require(config.get('set_event_notrace_pid', '') in ('', 'no pid'), 'notrace PID filter present')
        require(set(config['events']) == set(EVENTS), 'unexpected enabled event')
        for name, item in config['events'].items():
            require(item['enable'] == '1', 'required event not enabled')
            actual = re.sub(r'[\s()]', '', item['filter'])
            require(actual == re.sub(r'\s', '', self.plan.filters[name]), 'event filter mismatch')

    def load_owned(self):
        self.fs.no_links(self.evidence)
        self.fs.private_parent(self.evidence)
        self.state = json.loads(self.fs.read(self.state_path))
        require(self.state['schema'] == 'samurai-k459-trace-state-v1' and self.state['plan_key'] == self.plan.key and
                self.state['token'] == self.plan.token, 'receipt does not own this plan')
        require(self.state['boot_id'] == self.text(BOOT_ID), 'boot identity changed')
        require(self.state['instance_identity'] == self.fs.identity(self.plan.instance), 'instance replaced or absent')

    def start(self):
        p = self.plan
        possible = self.runtime_preflight()
        require(not self.fs.exists(p.instance), 'existing instance refused')
        require(not self.fs.exists(self.evidence), 'existing evidence directory refused')
        self.fs.private_parent(str(PurePosixPath(self.evidence).parent))
        self.fs.mkdir(self.evidence)
        lock = self.fs.lock(self.lock_path)
        self.state = dict(schema='samurai-k459-trace-state-v1', plan_key=p.key, token=p.token,
                          instance=p.instance, boot_id=self.text(BOOT_ID), phase='preparing',
                          possible_cpus=possible, online_cpus=p.online, errors=[], created_instance=False)
        try:
            self.state['unrelated_before'] = self.globals()
            self.save()
            self.fs.replace_private(self.evidence + '/probe-private.json', p.probe_bytes)
            self.fs.replace_private(self.evidence + '/selection-private.json', p.selection_bytes)
            self.fs.mkdir(p.instance)  # exclusive; a race must fail without touching the collided instance
            self.state['created_instance'] = True
            self.state['instance_identity'] = self.fs.identity(p.instance)
            self.save()
            self.own_write('tracing_on', '0')
            initial, _ = buffer_sizes(self.text(p.instance + '/buffer_total_size_kb'))
            require(0 < initial <= CREATE_LIMIT_KIB, 'new instance initial ring exceeded 16MiB')
            self.state['initial_main_ring_total_kib'] = initial
            self.own_write('events/enable', '0')
            self.own_write('current_tracer', 'nop')
            self.own_write('trace_clock', 'mono')
            self.own_write('tracing_cpumask', cpu_mask(p.online))
            # Guard worst-case possible CPUs before the allocation, then check the real total.
            self.own_write('buffer_size_kb', str(PER_CPU_KIB))
            require(int(self.text(p.instance + '/buffer_total_size_kb')) <= TOTAL_KIB, 'actual allocation too large')
            self.own_write('options/overwrite', '1')
            for field in ('set_event_pid', 'set_event_notrace_pid'):
                if self.fs.exists(p.instance + '/' + field):
                    self.own_write(field, '')
            self.own_write('trace', '')
            for name in EVENTS:
                require(self.fs.read(p.event_path(name, 'format')).decode() == p.probe['formats'][name], 'new instance format mismatch')
                self.own_write('events/' + name.replace(':', '/') + '/filter', p.filters[name])
                self.own_write('events/' + name.replace(':', '/') + '/enable', '1')
            self.state['configuration'] = self.config()
            self.check_config(self.state['configuration'])
            self.save()
            self.own_write('tracing_on', '1')
            require(self.text(p.instance + '/tracing_on') == '1', 'could not arm instance')
            self.state['phase'] = 'started'
            self.save()
        except Exception as error:
            self.state['errors'].append(dict(operation='start', error=repr(error)))
            self.state['phase'] = 'start_failed'
            # Only the instance created in this uninterrupted start can be rolled back.
            # Keep the private receipt even when rollback succeeds.
            if self.state['created_instance']:
                try:
                    self.own_write('tracing_on', '0')
                    self.state['failed_configuration'] = self.config()
                    require(self.state['instance_identity'] == self.fs.identity(p.instance), 'instance replaced before rollback')
                    self.fs.rmdir(p.instance)
                    self.state['rollback_removed_instance'] = True
                except Exception as cleanup:
                    self.state['errors'].append(dict(operation='rollback', error=repr(cleanup)))
                    self.state['rollback_removed_instance'] = False
            self.save()
            raise Rejected('start failed; private receipt includes rollback outcome') from error
        finally:
            self.fs.unlock(self.lock_path, lock)
        return self.state

    def stop_read(self):
        self.load_owned()
        lock = self.fs.lock(self.lock_path)
        original_phase = self.state['phase']
        try:
            require(self.state['phase'] in ('started', 'capture_failed'), 'stop-read phase refused')
            current = self.config()
            self.check_config(current)
            require(current == self.state['configuration'], 'owned configuration drifted')
            self.own_write('tracing_on', '0')
            require(self.text(self.plan.instance + '/tracing_on') == '0', 'instance did not stop')
            self.state['phase'] = 'stopped'
            self.save()
            attempt = len(self.state.get('capture_attempts', [])) + 1
            capture = dict(attempt=attempt, stats={}, complete=False)
            self.state.setdefault('capture_attempts', []).append(capture)
            self.save()
            capture['trace'] = self.fs.copy(self.plan.instance + '/trace',
                self.evidence + f'/trace-private-{attempt}.txt', EXPORT_MAX_BYTES)
            directories = self.fs.children(self.plan.instance + '/per_cpu')
            actual_cpus = sorted(int(name[3:]) for name in directories if re.fullmatch(r'cpu\d+', name))
            require(actual_cpus == self.state['possible_cpus'], 'per-CPU statistics set differs from possible CPUs')
            for number in actual_cpus:
                value = self.fs.read(self.plan.instance + f'/per_cpu/cpu{number}/stats', 65536)
                require(value.strip(), 'empty per-CPU statistics')
                self.fs.replace_private(self.evidence + f'/stats-private-{attempt}-cpu{number}.txt', value)
                capture['stats'][str(number)] = dict(bytes=len(value), sha256=digest(value))
            capture['online_cpus_after'] = cpus(self.text(SYS_ONLINE))
            capture['online_cpus_unchanged'] = capture['online_cpus_after'] == self.plan.online
            capture['unrelated_after'] = self.globals()
            capture['unrelated_selected_controls_unchanged'] = capture['unrelated_after'] == self.state['unrelated_before']
            capture['complete'] = True
            self.state['phase'] = 'captured'
            self.save()
        except Exception as error:
            self.state['errors'].append(dict(operation='stop_read', error=repr(error)))
            # Preserve a stopped instance for retry. Configuration/ownership failures may leave it running.
            self.state['phase'] = 'capture_failed' if original_phase in ('started', 'capture_failed') else original_phase
            self.save()
            raise
        finally:
            self.fs.unlock(self.lock_path, lock)
        return self.state

    def cleanup(self):
        self.load_owned()
        lock = self.fs.lock(self.lock_path)
        original_phase = self.state['phase']
        try:
            require(self.state['phase'] in ('captured', 'cleanup_failed'), 'capture must complete before cleanup')
            require(self.state['capture_attempts'][-1]['complete'], 'partial export cannot be deleted')
            require(self.text(self.plan.instance + '/tracing_on') == '0', 'instance still running')
            current = self.config()
            self.check_config(current)
            require(current == self.state['configuration'], 'owned configuration drifted')
            self.state['unrelated_at_cleanup'] = self.globals()
            self.state['unrelated_selected_controls_unchanged'] = self.state['unrelated_at_cleanup'] == self.state['unrelated_before']
            require(self.state['instance_identity'] == self.fs.identity(self.plan.instance), 'instance replaced before cleanup')
            self.fs.rmdir(self.plan.instance)
            require(not self.fs.exists(self.plan.instance), 'instance still exists after rmdir')
            self.state['phase'] = 'cleaned'
            self.save()
        except Exception as error:
            self.state['errors'].append(dict(operation='cleanup', error=repr(error)))
            self.state['phase'] = 'cleanup_failed' if original_phase in ('captured', 'cleanup_failed') else original_phase
            self.save()
            raise
        finally:
            self.fs.unlock(self.lock_path, lock)
        return self.state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', type=Path, required=True)
    parser.add_argument('--selection', type=Path, required=True)
    parser.add_argument('--extra', type=Path, required=True)
    parser.add_argument('--evidence-dir', required=True)
    parser.add_argument('--action', choices=('start', 'stop-read', 'cleanup'), default='start')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    plan = Plan(args.probe.read_bytes(), args.selection.read_bytes(), args.extra.read_bytes())
    session = Session(plan, RealFiles(), args.evidence_dir)
    if not args.execute:
        print(json.dumps(plan.render(args.action, session.evidence), indent=2))
        return
    require(os.geteuid() == 0, 'explicit execution requires root')
    result = getattr(session, args.action.replace('-', '_'))()
    print(json.dumps(dict(executed=True, phase=result['phase'], evidence_dir=session.evidence,
                          instance=plan.instance, errors=len(result['errors'])), indent=2))


if __name__ == '__main__':
    main()

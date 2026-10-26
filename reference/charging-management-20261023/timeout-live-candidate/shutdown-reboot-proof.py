"""Check actual cancellation/lock release during an already planned reboot."""
from pathlib import Path
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import signal
import stat
import time


def observe_shutdown(worker, expected_boot, boot, now, sleep, lock_path):
    io = worker.IO.__new__(worker.IO)
    io.lock = None
    io.parts = []
    io.load_closed = False
    io.now = now
    began = now()
    result = dict(passed=False, original_boot=expected_boot, started=began,
                  real_shutdown_detected=False, service_lock_released=False,
                  CPU_load_started=False, helper_control_writes=0,
                  error=None, cleanup_error=None, reason=None)
    try:
        assert boot() == expected_boot
        io.lock = os.open(lock_path, os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC)
        info = os.fstat(io.lock)
        assert stat.S_ISREG(info.st_mode) and info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o600
        fcntl.flock(io.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        io.save('shutdown-proof-ready.json', dict(pid=os.getpid(), boot=expected_boot,
                boottime=now(), lock_held=True, absolute_deadline=began + 30))
        while now() < began + 30:
            assert boot() == expected_boot
            if io.cancelled():
                event = worker.HERE / 'shutdown-observed.json'
                if event.exists():
                    result['event'] = json.loads(event.read_bytes())
                    result['real_shutdown_detected'] = (result['event']['action'] == 'openrc_shutdown'
                        and began <= result['event']['boottime'] <= now())
                    result['reason'] = 'openrc_shutdown' if result['real_shutdown_detected'] else 'other_cancel'
                else:
                    result['reason'] = 'signal_or_marker_cancel'
                break
            sleep(.25)
        else:
            result['reason'] = 'thirty_second_deadline'
    except BaseException as error:
        result['error'] = repr(error)
    finally:
        try:
            io.close()
            result['service_lock_released'] = io.lock is None
            result['released_at'] = now()
        except BaseException as error:
            result['cleanup_error'] = repr(error)
        result['passed'] = bool(result['real_shutdown_detected'] and
            result['service_lock_released'] and result['error'] is None and result['cleanup_error'] is None)
        io.save('shutdown-proof-result.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--boot', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    assert args.execute and os.geteuid() == 0 and not __import__('sys').flags.optimize
    assert os.uname().version == '#506 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
    root = Path(__file__).resolve().parent
    pins = json.loads((root / 'source-pins.json').read_bytes())
    for name, expected in pins.items():
        assert Path(name).name == name and hashlib.sha256((root / name).read_bytes()).hexdigest() == expected
    assert not (root / 'shutdown-proof-ready.json').exists() and not (root / 'shutdown-proof-result.json').exists()
    assert not (root / 'shutdown-observed.json').exists()
    spec = importlib.util.spec_from_file_location('actual_timer_cancel_worker', root / 'worker.py')
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    signal.signal(signal.SIGTERM, worker.cancel)
    signal.signal(signal.SIGINT, worker.cancel)
    result = observe_shutdown(worker, args.boot,
        lambda: Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        lambda: time.clock_gettime(time.CLOCK_BOOTTIME), time.sleep,
        '/run/lock/samurai-charging.lock')
    print(json.dumps(result))
    return 0 if result['passed'] else 3


if __name__ == '__main__':
    raise SystemExit(main())

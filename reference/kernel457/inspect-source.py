"""Read exact441 FULL/vb2/IRQ source and original363 tracing configuration."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel457')
spec = importlib.util.spec_from_file_location('storage449', HERE.parent/'kernel449/storage.py')
storage = importlib.util.module_from_spec(spec); spec.loader.exec_module(storage)
BUILD = storage.mount.mounted_build()
SOURCE = BUILD.parent/'source354'
HEAD = '5b0e7a9ac5b311a4c4fe17cf48b7ed4fc9a7b91d'
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS='0')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(['git', '-C', str(SOURCE), *args], env=ENV)


def main():
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    assert git('rev-parse', 'HEAD').decode().strip() == HEAD
    assert not git('status', '--porcelain')
    index = Path(git('rev-parse', '--absolute-git-dir').decode().strip())/'index'
    index_before = sha(index)
    fixed = json.loads((HERE.parent/'kernel441/kernel-source-state.json').read_text())
    assert fixed['commit'] == HEAD
    assert all(sha(SOURCE/row['path']) == row['sha256'] for row in fixed['source_hashes'])
    receipt = json.loads((HERE.parent/'kernel441/intree-build-validation.json').read_text())
    assert receipt['passed']
    modules = {row['name']: row['sha256'] for row in receipt['modules'] if row['runtime_candidate']}
    for row in receipt['modules']:
        if row['runtime_candidate']:
            assert sha(row['private_path']) == row['sha256']
    record363 = json.loads((HERE.parent/'kernel363/boot-candidate-build-validation.json').read_text())
    image = PRIVATE.parent/'kernel363/Image-k363-private'
    assert sha(image) == record363['artifacts']['arch/arm64/boot/Image']['sha256']
    config = subprocess.check_output([str(SOURCE/'scripts/extract-ikconfig'), str(image)])
    assert hashlib.sha256(config).hexdigest() == record363['artifacts']['.config']['sha256']
    (PRIVATE/'config363-private').write_bytes(config)
    prefixes = ['CONFIG_TRAC', 'CONFIG_FTRACE', 'CONFIG_FUNCTION_TRAC', 'CONFIG_DYNAMIC_FTRACE',
                'CONFIG_KPROBE', 'CONFIG_UPROBE', 'CONFIG_PERF_EVENTS', 'CONFIG_BPF', 'CONFIG_EVENT_TRACING',
                'CONFIG_HAVE_SYSCALL_TRACEPOINTS', 'CONFIG_FPROBE', 'CONFIG_DEBUG_FS']
    selected = [line for line in config.decode().splitlines() if any(prefix in line for prefix in prefixes)]
    paths = list((SOURCE/'drivers/media/platform/qcom/camss').glob('camss-vfe*.c'))
    paths += [SOURCE/'drivers/media/platform/qcom/camss'/name for name in
              ['camss-vfe.h', 'camss-video.c', 'camss-video.h', 'camss.c', 'camss-csid.c', 'camss-csid-gen2.c']]
    paths += [SOURCE/name for name in ['drivers/media/common/videobuf2/videobuf2-core.c',
              'drivers/media/common/videobuf2/videobuf2-v4l2.c', 'include/media/videobuf2-core.h',
              'include/trace/events/vb2.h', 'include/trace/events/v4l2.h',
              'include/media/videobuf2-v4l2.h', 'include/trace/events/irq.h',
              'drivers/media/common/videobuf2/vb2-trace.c',
              'drivers/media/v4l2-core/v4l2-trace.c', 'drivers/media/v4l2-core/v4l2-ioctl.c',
              'drivers/media/v4l2-core/v4l2-event.c',
              'drivers/media/platform/qcom/camss/Makefile',
              'kernel/trace/trace_events.c', 'kernel/trace/trace_kprobe.c', 'kernel/trace/trace_events_hist.c']]
    rows = []
    for path in sorted(set(paths)):
        if not path.is_file():
            continue
        relative = str(path.relative_to(SOURCE))
        raw = path.read_bytes()
        assert raw == git('show', HEAD+':'+relative)
        target = PRIVATE/'source'/relative
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        target.write_bytes(raw)
        baseline = subprocess.run(['git', '-C', str(SOURCE), 'show', record363['commit']+':'+relative],
                                  env=ENV, capture_output=True)
        assert baseline.returncode in [0, 128]
        rows.append(dict(path=relative, sha256=hashlib.sha256(raw).hexdigest(),
                         exists_in_original363=baseline.returncode == 0,
                         same_as_original363=baseline.returncode == 0 and baseline.stdout == raw,
                         lines=len(raw.splitlines())))
    trace_calls = git('grep', '-n', '-E',
                      r'trace_(vb2_v4l2|v4l2_(qbuf|dqbuf))', HEAD,
                      '--', 'drivers', 'include').decode().splitlines()
    assert len(trace_calls) == 2
    assert all('drivers/media/v4l2-core/v4l2-ioctl.c:' in line for line in trace_calls)
    assert not any('trace_vb2_v4l2_' in line for line in trace_calls)
    user_state = json.loads((HERE.parent/'kernel452/source-state.json').read_text())
    user_source = Path(user_state['source'])
    user_hashes = {row['path']: row['sha256'] for row in user_state['source_hashes']}
    user_rows = []
    for relative in ['src/libcamera/v4l2_videodevice.cpp', 'src/libcamera/v4l2_subdevice.cpp',
                     'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp',
                     'src/libcamera/pipeline/camss-vfe/full_ownership_trace.h']:
        path = user_source/relative
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if relative in user_hashes:
            assert digest == user_hashes[relative]
        target = PRIVATE/'userspace452'/relative
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        target.write_bytes(raw)
        assert sha(path) == digest
        user_rows.append(dict(path=relative, sha256=digest, lines=len(raw.splitlines()),
                              checked_against_frozen_source_state=relative in user_hashes))
    assert sha(index) == index_before and not git('status', '--porcelain')
    report = dict(stage=457, source_head=HEAD, modules441=modules,
                  original363_config_sha256=hashlib.sha256(config).hexdigest(), selected_tracing_config=selected,
                  exact_v4l2_trace_calls=trace_calls,
                  vb2_v4l2_events_declared_and_exported_but_no_callers=True,
                  userspace452_clock_sources=user_rows,
                  files=rows, free_ext4_bytes=shutil.disk_usage(BUILD).free,
                  source_shared_index_unchanged=True, compiled=False,
                  phone_or_sdk_accessed=False, passed=True)
    (HERE/'source-inspection.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'files'}, indent=2))


if __name__ == '__main__':
    main()

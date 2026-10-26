"""Read-only fixed-kernel source proof for the lifecycle helper's memory limits."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel459')
HEAD = '5b0e7a9ac5b311a4c4fe17cf48b7ed4fc9a7b91d'
ORIGINAL = 'ba61a62293e0f6bc5838c06f2e85e033e3d702a8'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    spec = importlib.util.spec_from_file_location('storage449', HERE.parent/'kernel449/storage.py')
    storage = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(storage)
    build = storage.mount.mounted_build()
    source = build.parent/'source354'
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
    def git(*args):
        return subprocess.check_output(['git', '-C', str(source), *args], env=env)
    assert git('rev-parse', 'HEAD').decode().strip() == HEAD and not git('status', '--porcelain')
    index = Path(git('rev-parse', '--absolute-git-dir').decode().strip())/'index'
    before = sha(index.read_bytes())
    rows = []
    content = {}
    for relative in ['kernel/trace/trace.c', 'kernel/trace/trace_snapshot.c', 'kernel/trace/ring_buffer.c']:
        raw = (source/relative).read_bytes()
        assert raw == git('show', HEAD+':'+relative) == git('show', ORIGINAL+':'+relative)
        target = PRIVATE/'source'/relative
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        target.write_bytes(raw)
        rows.append(dict(path=relative, sha256=sha(raw), equal_original363=True))
        content[relative] = raw.decode()
    assert '#define TRACE_BUF_SIZE_DEFAULT\t1441792UL' in content['kernel/trace/trace.c']
    assert 'allocate_trace_buffers(tr, trace_buf_size)' in content['kernel/trace/trace.c']
    assert 'allocate_snapshot ? size : 1' in content['kernel/trace/trace_snapshot.c']
    assert 'nr_pages = DIV_ROUND_UP(size, rb_subbuf_capacity(buffer))' in content['kernel/trace/ring_buffer.c']
    assert 'return rb_subbuf_capacity(buffer) * buffer->buffers[cpu]->nr_pages;' in content['kernel/trace/ring_buffer.c']
    config = (PRIVATE.parent/'kernel457/config363-private').read_bytes()
    assert sha(config) == '23e088a90736bbbc442c672d82b35c11bf04f7dc489f1c6afb1b03dc0d8f30ed'
    assert b'CONFIG_ARM64_4K_PAGES=y\n' in config and b'CONFIG_TRACER_SNAPSHOT=y\n' in config
    extra_bytes = (PRIVATE.parent/'kernel457/trace-extra-private.json').read_bytes()
    extra = json.loads(extra_bytes)
    mem = next(int(line.split()[1]) for line in extra['meminfo'].splitlines() if line.startswith('MemAvailable:'))
    assert extra['phone_changed'] is False and extra['online_cpus'] == '0-7'
    assert extra['buffer_size_kb'].strip() == '7 (expanded: 1408)'
    assert extra['buffer_total_size_kb'].strip() == '56 (expanded: 11264)'
    assert mem >= 524288
    assert sha(index.read_bytes()) == before and not git('status', '--porcelain')
    report = dict(stage=459, source_head=HEAD, original363=ORIGINAL, files=rows,
                  config363_sha256=sha(config), arm64_page_bytes=4096,
                  default_main_ring_request_bytes_per_cpu=1441792,
                  online_cpu_count=8, nominal_initial_main_ring_kib=11264,
                  initial_creation_main_ring_limit_kib=16384,
                  requested_steady_main_ring_kib_per_cpu=512,
                  requested_steady_total_kib=4096, reported_data_capacity_can_round_up=True,
                  allowed_reported_rounding_per_cpu_less_than_kib=4,
                  steady_main_ring_limit_kib=8192,
                  snapshot_minimal_buffer_allocated_but_not_armed=True,
                  size_limits_describe_trace_ring_capacity_not_total_allocator_rss=True,
                  mem_available_kib_from_readonly_extra=mem, minimum_mem_available_kib=524288,
                  extra_source_sha256=sha(extra_bytes),
                  global_current7kib_not_used_as_new_instance_default=True,
                  full_cmdline_and_unrelated_odm_details_kept_private=True,
                  shared_source_index_unchanged=True, no_phone_sdk_compile=True, passed=True)
    (HERE/'capacity-source-validation.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(stage=459, passed=True, nominal_initial_ring_kib=11264,
                          mem_available_kib=mem, no_phone_sdk_compile=True)))


if __name__ == '__main__':
    main()

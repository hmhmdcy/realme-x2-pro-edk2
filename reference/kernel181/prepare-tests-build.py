from pathlib import Path
import ast
import hashlib
import json
import re
import subprocess

root = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel181')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
prior = json.loads((ref.parent / 'kernel180/build-package-validation.json').read_text())
hashes = dict(prior['source_sha256'])
for name, digest in hashes.items():
    if name != 'drivers/mfd/wcd934x.c':
        assert sha(root / name) == digest, name
hashes['drivers/mfd/wcd934x.c'] = sha(root / 'drivers/mfd/wcd934x.c')
assert (root / '.config').read_bytes() == (out / 'config-before-private').read_bytes()
subprocess.run(['git', 'diff', '--check'], cwd=root, check=True)
manifest = dict(stage=181, baseline_kernel=180, source_sha256=hashes, checkpatch_pass=True,
                modified_this_stage=['drivers/mfd/wcd934x.c'], pdr180_preserved=True,
                main_cache_type_maple_unchanged=True, interface_cache_policy_unchanged=True,
                offline_cleanup_discarded_cache_never_replayed=True, build_and_runtime_pending=True)
for folder in (ref, out):
    (folder / 'source-validation.json').write_text(json.dumps(manifest, indent=2) + '\n')

s = (ref.parent / 'kernel180/test-reset-and-irq.py').read_text()
s = s.replace('kernel180', 'kernel181').replace('stage=180', 'stage=181').replace('pdr-and-parent-irq.patch', 'offline-irq-cleanup.patch')
s = s.replace("core=(k/'drivers/slimbus/core.c').read_text();mfd=(k/'drivers/mfd/wcd934x.c').read_text()",
              "core=(k/'drivers/slimbus/core.c').read_text();mfd=(k/'drivers/mfd/wcd934x.c').read_text()\n"
              "regcore=(k/'drivers/base/regmap/regmap.c').read_text();regcache=(k/'drivers/base/regmap/regcache.c').read_text()\n"
              "actual_cache=function(regcache,'regcache_cache_only')\nactual_write=function(regcore,'_regmap_write')\nactual_read=function(regcore,'_regmap_read')")
old = 'struct regmap{struct slim_device *sdev;};'
assert old in s
s = s.replace(old, '''struct regmap{
 struct slim_device *sdev;bool cache_only,cache_bypass,defer_caching,cache_dirty,locked,cache_valid;
 int cache_type;unsigned cached_reg,cached_value;void *lock_arg;
 void (*lock)(void *);void (*unlock)(void *);
 int (*reg_write)(void *,unsigned,unsigned);int (*reg_read)(void *,unsigned,unsigned *);
};
#define REGCACHE_NONE 0
#define REGCACHE_MAPLE 1
#define WARN_ON(c) assert(!(c))
#define trace_regmap_cache_only(...) ((void)0)
#define trace_regmap_reg_write(...) ((void)0)
#define trace_regmap_reg_read(...) ((void)0)
static unsigned live_writes,offline_attempts,software_writes;
static void map_lock(void *p){struct regmap *m=p;assert(!m->locked);m->locked=true;}
static void map_unlock(void *p){struct regmap *m=p;assert(m->locked);m->locked=false;}
static void *_regmap_map_get_context(struct regmap *m){return m;}
static bool regmap_writeable(struct regmap *m,unsigned r){return r<=0xffff;}
static bool regmap_readable(struct regmap *m,unsigned r){return r<=0xffff;}
static bool regmap_should_log(struct regmap *m){return false;}
static int regcache_write(struct regmap *m,unsigned r,unsigned v){assert(m->locked);software_writes++;if(r!=0xfffe){m->cache_valid=true;m->cached_reg=r;m->cached_value=v;}return 0;}
static int regcache_read(struct regmap *m,unsigned r,unsigned *v){assert(m->locked);if(m->cache_valid&&m->cached_reg==r&&r!=0xfffe){*v=m->cached_value;return 0;}return -ENOENT;}
static int _regmap_write(struct regmap *,unsigned,unsigned);
static int _regmap_read(struct regmap *,unsigned,unsigned *);
void regcache_cache_only(struct regmap *,bool);
''')
s = s.replace('struct regmap *m=malloc(sizeof(*m));assert(m);m->sdev=s;map_count++;return m;',
              'struct regmap *m=calloc(1,sizeof(*m));assert(m);m->sdev=s;m->cache_type=REGCACHE_MAPLE;'
              'm->lock=map_lock;m->unlock=map_unlock;m->lock_arg=m;map_count++;return m;')
old = 'static int regmap_write(struct regmap *m,int r,int v){assert(m->sdev->laddr==m->sdev->hardware_laddr);return fail_io()?-EIO:0;}'
assert old in s
s = s.replace(old, '''static int hardware_write(void *p,unsigned r,unsigned v){struct regmap *m=p;assert(m->locked);if(m->sdev->status==SLIM_DEVICE_STATUS_DOWN){offline_attempts++;return -ENOTCONN;}assert(m->sdev->laddr==m->sdev->hardware_laddr);live_writes++;return fail_io()?-EIO:0;}
static int hardware_read(void *p,unsigned r,unsigned *v){struct regmap *m=p;assert(m->locked);if(m->sdev->status==SLIM_DEVICE_STATUS_DOWN){offline_attempts++;return -ENOTCONN;}*v=0;return 0;}
static int regmap_write(struct regmap *m,int r,int v){m->reg_write=hardware_write;m->reg_read=hardware_read;m->lock(m->lock_arg);int ret=_regmap_write(m,r,v);m->unlock(m->lock_arg);return ret;}
''')
old = "if(!io_fail)assert(!irq_enabled&&!irq_inflight);children=0;"
assert old in s
s = s.replace(old, "if(!io_fail)assert(!irq_enabled&&!irq_inflight);"
              "struct regmap *m=((struct wcd934x_ddata *)main_dev.dev.data)->regmap;"
              "assert(m->cache_only==(main_dev.status==SLIM_DEVICE_STATUS_DOWN));"
              "unsigned writes=live_writes,bad=offline_attempts;"
              "for(int irq=0;irq<6;irq++)for(int reg=0;reg<13;reg++)assert(regmap_write(m,0x220+reg,1)==0);"
              "if(main_dev.status==SLIM_DEVICE_STATUS_DOWN){assert(live_writes==writes&&offline_attempts==bad&&m->cache_dirty);"
              "unsigned value=99;m->lock(m->lock_arg);assert(_regmap_read(m,0xfffe,&value)==-EBUSY&&value==99);"
              "assert(_regmap_read(m,0x22c,&value)==0&&value==1);assert(_regmap_write(m,0x10000,1)==-EIO);"
              "m->unlock(m->lock_arg);assert(offline_attempts==bad);}"
              "else assert(live_writes==writes+78);children=0;")
s = s.replace('mode=m;io_fail=io;irq_enabled=irq_inflight=false;',
              'mode=m;io_fail=io;irq_enabled=irq_inflight=false;live_writes=offline_attempts=software_writes=0;')
s = s.replace('assert(irq_enabled);assert(wcd934x_slim_status(&main_dev,SLIM_DEVICE_STATUS_DOWN)==0);',
              'assert(irq_enabled);main_dev.status=SLIM_DEVICE_STATUS_DOWN;assert(wcd934x_slim_status(&main_dev,SLIM_DEVICE_STATUS_DOWN)==0);')
s = s.replace('assert(wcd934x_slim_status(&main_dev,SLIM_DEVICE_STATUS_UP)==0&&irq_enabled&&irq_count==1);',
              'main_dev.status=SLIM_DEVICE_STATUS_UP;assert(wcd934x_slim_status(&main_dev,SLIM_DEVICE_STATUS_UP)==0&&irq_enabled&&irq_count==1);'
              'assert(!wcd934x_get_private(&main_dev)->ddata.regmap->cache_only);')
old = 'code=prefix+defines+private+absent+get_addr+actual+bridge+core_probe+tests'
assert old in s
s = s.replace(old, 'code=prefix+defines+private+actual_cache+actual_write+actual_read+absent+get_addr+actual+bridge+core_probe+tests')
marker = "probe_result=run('reset-probe',code)"
s = s.replace(marker, marker + "\nrun('negative-offline-cache-disabled',code.replace('\\t\\tregcache_cache_only(ddata->regmap, true);','\\t\\t(void)ddata;'),False)\n"
              "run('negative-cache-on-live-removal',code.replace('\\tif (sdev->status == SLIM_DEVICE_STATUS_DOWN)','\\tif (true)'),False)")
s = s.replace("'parent-nosync'],", "'parent-nosync','offline-cache-disabled','cache-on-live-removal'],")
s = s.replace('parent_irq_quiesce_before_children_verified=True,',
              'actual_regcache_mode_and_internal_read_write_executed=True,uncached_offline_read_returns_EBUSY_without_fake_value=True,invalid_offline_write_error_preserved=True,offline_hardware_access_rejected=True,live_cleanup_hardware_io_preserved=True,old_cache_destroyed_and_fresh_map_active=True,parent_irq_quiesce_before_children_verified=True,')
ast.parse(s)
(ref / 'test-offline-cleanup.py').write_text(s)

build = (ref.parent / 'kernel180/build-package.py').read_text()
build = build.replace('kernel180', 'kernel181').replace('k180', 'k181').replace('K180', 'K181')
build = build.replace("KBUILD_BUILD_VERSION='180'", "KBUILD_BUILD_VERSION='181'").replace("'#180 SMP PREEMPT'", "'#181 SMP PREEMPT'")
build = build.replace('stage=180,kernel_build=180', 'stage=181,kernel_build=181').replace('modules-root180', 'modules-root181')
build = build.replace("ref.parent/'kernel176/build-package-validation.json'", "ref.parent/'kernel180/build-package-validation.json'")
build = build.replace("assert json.loads((ref/'pdr-host-validation.json').read_text())['all_passed']",
                      "pdr_test=json.loads((ref.parent/'kernel180/pdr-host-validation.json').read_text())\n"
                      "assert pdr_test['all_passed'] and pdr_test['actual_pdr_source_sha256']==source['source_sha256']['drivers/soc/qcom/pdr_interface.c']")
build = build.replace("rollback=out.parent/'kernel176/logdump-k176-reset.img'", "rollback=out.parent/'kernel180/logdump-k180-pdr-irq.img'")
build = build.replace('rollback176_sha256', 'rollback180_sha256')
build = build.replace('Image-k181-pdr-irq-private', 'Image-k181-offline-irq-private').replace('logdump-k181-pdr-irq.img', 'logdump-k181-offline-irq.img')
build = build.replace('pdr_transaction_peer_and_lifetime_fix_included=True,', 'offline_main_irq_cache_cleanup_included=True,pdr_transaction_peer_and_lifetime_fix_included=True,')
ast.parse(build)
(ref / 'build-package.py').write_text(build)
print('K181_OFFLINE_FUNCTION_TEST_AND_BUILD_PREPARED')

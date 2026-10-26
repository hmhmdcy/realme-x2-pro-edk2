"""Run actual C handoff and extracted owner lifecycle with sanitizers, offline."""
from pathlib import Path
import hashlib,json,re,subprocess
HERE=Path(__file__).resolve().parent
BUILD=HERE/'test-build'
BUILD.mkdir(exist_ok=True)
INC=BUILD/'include'
(INC/'linux/usb').mkdir(parents=True,exist_ok=True)
kernel='''#ifndef TEST_KERNEL_H
#define TEST_KERNEL_H
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <errno.h>
#include <string.h>
#include <pthread.h>
typedef int64_t s64;
#define BIT(n) (1U<<(n))
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define GFP_KERNEL 0
#define IS_ENABLED(x) 1
#define ERR_PTR(e) ((void *)(intptr_t)(e))
#define PTR_ERR(p) ((intptr_t)(p))
#define IS_ERR(p) ((uintptr_t)(p)>(uintptr_t)-4096)
struct regmap { unsigned int r[8192]; };
struct device { int unused; };
struct mutex { pthread_mutex_t m; };
static inline void mutex_init(struct mutex *m) { pthread_mutex_init(&m->m,NULL); }
static inline void mutex_lock(struct mutex *m) { pthread_mutex_lock(&m->m); }
static inline void mutex_unlock(struct mutex *m) { pthread_mutex_unlock(&m->m); }
void *devm_kzalloc(struct device *,size_t,int);
int devm_add_action_or_reset(struct device *,void (*)(void *),void *);
s64 ktime_get_boottime(void);
s64 ktime_to_ms(s64);
void msleep(unsigned int);
int regmap_read(struct regmap *,unsigned int,unsigned int *);
int regmap_update_bits(struct regmap *,unsigned int,unsigned int,unsigned int);
#endif
'''
(INC/'test-kernel.h').write_text(kernel)
for h in ['bitops','delay','device','err','ktime','mutex','regmap','slab','string','kconfig']:
    (INC/f'linux/{h}.h').write_text('#include "test-kernel.h"\n')
(INC/'linux/errno.h').write_text('#include_next <linux/errno.h>\n')
(INC/'linux/usb/samurai-tcpm-apsd.h').write_bytes((HERE/'samurai-tcpm-apsd.h').read_bytes())

def extract(text,name):
    m=re.search(r'^(?:static\s+)?(?:int|bool|void)\s+'+re.escape(name)+r'\([^;]+?\)\n\{',text,re.M)
    assert m,name
    start=m.start();pos=m.end();depth=1
    while depth:
        if text[pos]=='{':depth+=1
        elif text[pos]=='}':depth-=1
        pos+=1
    return text[start:pos]+'\n'

owner=(HERE/'samurai-apsd-owner.c').read_text()
functions=['owner_aborted','owner_queue','owner_join','samurai_apsd_tcpm_quiesce','samurai_apsd_tcpm_release']
(BUILD/'owner-functions.inc').write_text('\n'.join(extract(owner,n) for n in functions))
rows=[]
for name,source in [('handoff',HERE/'test-handoff.c'),('owner',HERE/'test-owner.c')]:
    exe=BUILD/('test-'+name)
    argv=['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter',
          '-Wno-sign-compare','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',
          '-pthread','-I'+str(INC),'-I'+str(HERE),'-I'+str(BUILD),str(source),'-o',str(exe)]
    build=subprocess.run(argv,text=True,capture_output=True)
    assert build.returncode==0,build.stderr
    run=subprocess.run([str(exe)],text=True,capture_output=True,timeout=15)
    assert run.returncode==0,(run.returncode,run.stdout,run.stderr)
    rows.append({'name':name,'passed':True,'stdout':run.stdout.strip(),
                 'sanitizers':['ASan','UBSan'],'compiler_diagnostics':build.stderr})

# Check actual integration sites, including the earlier PHY-start boundary.
driver=(HERE/'qcom_pmic_typec.c').read_text()
phy=(HERE/'qcom_pmic_typec_pdphy.c').read_text()
probe=extract(driver,'qcom_pmic_typec_probe')
assert probe.index('qcom_pmic_typec_apsd_prepare(dev, regmap)') < probe.index('tcpm_register_port(')
rx=extract(phy,'qcom_pmic_typec_pdphy_set_pd_rx')
assert 'if (on)' in rx and rx.index('qcom_pmic_typec_apsd_verify') < rx.index('spin_lock_irqsave')
assert 'quiesce' not in rx and 'release' not in rx
tx=extract(phy,'qcom_pmic_typec_pdphy_pd_transmit')
assert tx.index('qcom_pmic_typec_apsd_verify') < tx.index('if (msg)')
start=extract(phy,'qcom_pmic_typec_pdphy_start')
assert start.index('qcom_pmic_typec_apsd_verify') < start.index('regulator_enable')
assert 'qcom_pmic_typec_apsd.o' in (HERE/'Makefile').read_text()
assert 'READ_ONCE(tcpm_fenced)' in extract(owner,'owner_aborted')
assert 'READ_ONCE(tcpm_fenced)' in extract(owner,'owner_queue')
rows.append({'name':'actual-integration','passed':True,'assertions':10})
result={'passed':True,'phone_accessed':False,'complete_coexistence':False,
        'tests':rows,'extracted_functions':functions,
        'production_sources':{n:hashlib.sha256((HERE/n).read_bytes()).hexdigest()
          for n in ['qcom_pmic_typec_apsd.c','samurai-apsd-owner.c','qcom_pmic_typec.c','qcom_pmic_typec_pdphy.c']}}
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))

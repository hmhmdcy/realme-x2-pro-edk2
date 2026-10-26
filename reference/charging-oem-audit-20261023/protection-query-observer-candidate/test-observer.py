"""Build/run changed actual functions with fake kernel/I2C boundaries only."""
from pathlib import Path
import hashlib,json,re,subprocess
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
PRIVATE=Path('/home/cy122/charging-management-20261023/protection-query-observer-tests-r2')
PRIVATE.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
fixture=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/window2/packets-private.bin')
assert sha(fixture)=='662254550a4f08ed8d0b1f9b1b58139e10cec0ceace5d2b222c438730d7d5ca2'
source=(HERE/'samurai-gauge-protection.c').read_text()
def function(s,name):
 match=re.search(r'^static (?:inline )?(?:int|ssize_t) '+name+r'\([^;]*?\)\s*\{',s,re.M);assert match,name
 at=s.index('{',match.start());end=at+1;level=1
 while level:level+=(s[end]=='{')-(s[end]=='}');end+=1
 return s[match.start():end]
names=['sm_protection_read','sm_protection_capture_locked','mac_evidence_capture_store','mac_evidence_show']
declarations=source[source.index('static const unsigned int sm_evidence_commands'):source.index('static struct platform_device *sm_board;')]
actual=declarations+'\n'+'\n\n'.join(function(source,n) for n in names)+'\n'
(PRIVATE/'actual-provider.inc').write_text(actual)
stub=PRIVATE/'stubs/linux';stub.mkdir(parents=True)
(stub/'delay.h').write_text('void usleep_range(unsigned long,unsigned long);\n')
(stub/'ktime.h').write_text('typedef unsigned long long u64;\nunsigned long long ktime_get_boottime_ns(void);\n')
(stub/'i2c.h').write_text('''#ifndef FAKE_I2C_H
#define FAKE_I2C_H
#include <stdbool.h>
#include <stddef.h>
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define I2C_SMBUS_READ 1
#define I2C_SMBUS_WRITE 0
#define I2C_SMBUS_WORD_DATA 3
#define I2C_M_RD 1
struct i2c_adapter { int unused; };
struct i2c_client { struct i2c_adapter *adapter;unsigned short addr,flags; };
union i2c_smbus_data { unsigned short word; };
struct i2c_msg { unsigned short addr,flags,len;unsigned char *buf; };
int __i2c_smbus_xfer(struct i2c_adapter *,unsigned short,unsigned short,char,unsigned char,int,union i2c_smbus_data *);
int __i2c_transfer(struct i2c_adapter *,struct i2c_msg *,int);
#endif
''')
oldbase=REF/'charging-session-20261023/r8-source-integration/kernel-sources/drivers/power/supply'
old=(oldbase/'samurai-gauge-protection.c').read_text()
assert function(old,'sm_protection_read')==function(source,'sm_protection_read')
for n in ['sm_protection_get','protection_state_show','sm_protection_probe']:
 assert function(old,n)==function(source,n),n
assert 'DEVICE_ATTR(mac_evidence_capture, 0200, NULL, mac_evidence_capture_store)' in source
assert 'DEVICE_ATTR(mac_evidence, 0400, mac_evidence_show, NULL)' in source
assert not re.search(r'(?:sm_protection_capture_locked|sm_gauge_mac_observe_locked)\(',function(source,'sm_protection_read'))
command=['gcc','-std=c11','-g','-O1','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-sign-compare',
 '-Wno-misleading-indentation','-fsanitize=address,undefined','-fno-omit-frame-pointer','-pthread',
 '-I'+str(stub.parent),'-I'+str(HERE),'-I'+str(PRIVATE),str(HERE/'test-observer.c'),'-o',str(PRIVATE/'test-observer')]
compiled=subprocess.run(command,capture_output=True,text=True)
(PRIVATE/'compile.log').write_text(compiled.stdout+compiled.stderr)
assert compiled.returncode==0,compiled.stdout+compiled.stderr
run=subprocess.run([str(PRIVATE/'test-observer'),str(fixture)],capture_output=True,text=True)
(PRIVATE/'run.log').write_text(run.stdout+run.stderr)
assert run.returncode==0,run.stdout+run.stderr
data=json.loads(run.stdout)
result={'passed':True,'actual':data,'command':command,'compile_returncode':compiled.returncode,'run_returncode':run.returncode,
 'private_output':str(PRIVATE),'actual_function_source_sha256':sha(PRIVATE/'actual-provider.inc'),
 'actual_functions':{n:hashlib.sha256(function(source,n).encode()).hexdigest() for n in names},
 'test_binary_sha256':sha(PRIVATE/'test-observer'),'compile_log_sha256':sha(PRIVATE/'compile.log'),'run_log_sha256':sha(PRIVATE/'run.log'),
 'tested_files':{n:sha(HERE/n) for n in ['gauge-protocol.h','gauge-i2c.h','samurai-gauge-protection.c','test-observer.c','test-observer.py']},
 'old6_packet_fixture_sha256':sha(fixture),'old149_classifier_receipt_sha256':sha(HERE.parent/'tca-classifier/test-result.json'),
 'unmodified_normal_functions':['sm_protection_read','sm_protection_get','protection_state_show','sm_protection_probe'],
 'old_suites_rerun':False,'device_SSH_USB_SDK_Git_accessed':False,'boundary':'real new functions/header; OS/I2C fake; not probe/physical or 2719 compatibility proof'}
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':True,**data,'receipt_sha256':sha(HERE/'test-result.json')}))

"""Offline fault injection into the production gauge transport, no phone I/O."""
from pathlib import Path
import hashlib
import json
import subprocess

ref = Path(__file__).resolve().parent
work = Path('/home/cy122/charging-management-20261023/transport-test')
stub = work / 'stubs/linux'
stub.mkdir(parents=True, exist_ok=True)
(stub / 'delay.h').write_text('void usleep_range(unsigned long, unsigned long);\n')
(stub / 'i2c.h').write_text('''#ifndef TEST_LINUX_I2C_H
#define TEST_LINUX_I2C_H
#include <stdbool.h>
#define ARRAY_SIZE(x) (sizeof(x) / sizeof((x)[0]))
#define I2C_SMBUS_READ 1
#define I2C_SMBUS_WRITE 0
#define I2C_SMBUS_WORD_DATA 3
#define I2C_M_RD 1
struct i2c_adapter { int unused; };
struct i2c_client { struct i2c_adapter *adapter; unsigned short addr, flags; };
union i2c_smbus_data { unsigned short word; };
struct i2c_msg { unsigned short addr, flags, len; unsigned char *buf; };
int __i2c_smbus_xfer(struct i2c_adapter *, unsigned short, unsigned short,
                    char, unsigned char, int, union i2c_smbus_data *);
int __i2c_transfer(struct i2c_adapter *, struct i2c_msg *, int);
#endif
''')
fixture = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/window2/packets-private.bin')
previous = json.loads((ref / 'protocol-test-result.json').read_text())
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(fixture) == previous['real_fixture_sha256']
binary = work / 'test-gauge-transport'
command = ['gcc', '-std=c11', '-g', '-Wall', '-Wextra', '-Werror',
           '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
           '-I' + str(stub.parent), '-I' + str(ref),
           str(ref / 'test-gauge-transport.c'), '-o', str(binary)]
subprocess.run(command, check=True)
result = subprocess.run([str(binary), str(fixture)], capture_output=True, text=True)
print(result.stdout, end=''); print(result.stderr, end=''); result.check_returncode()
report = json.loads(result.stdout)
report.update({'scope': 'Actual gauge-i2c.h; only kernel bus and delay boundary substituted. No new hardware reads or configuration writes.',
               'sanitizers': ['ASan', 'UBSan'], 'real_fixture_sha256': digest(fixture),
               'tested_files': {n: digest(ref / n) for n in
                                ['gauge-i2c.h', 'gauge-protocol.h', 'test-gauge-transport.c', 'test-gauge-transport.py']}})
(ref / 'gauge-transport-test-result.json').write_text(json.dumps(report, indent=2) + '\n')

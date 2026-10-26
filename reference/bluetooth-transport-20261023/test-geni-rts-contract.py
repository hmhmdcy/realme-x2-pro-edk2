"""Exercise extracted GENI/core functions, including lock and serdev contracts.

The host shim models kernel IRQ/save and registers. It is not kernel lockdep or
an assertion that this defect caused the historical phase-5 receive failure.
Only this directory is written; no live kernel tree, SDK or device is changed.
"""
from pathlib import Path
import ast
import difflib
import hashlib
import json
import re
import subprocess

R = Path(__file__).resolve().parent
S = R / 'source'
driver = (S / 'qcom_geni_serial.c').read_text()
core = (S / 'serial_core.c').read_text()
serdev = (S / 'serdev-ttyport.c').read_text()


def function(source, name):
    start = source.index(name + '(')
    start = source.rfind('\n', 0, start) + 1
    if source[start:start + len(name)] == name:
        start = source.rfind('\n', 0, start - 1) + 1
    brace = source.index('{', start)
    level, end = 1, brace + 1
    while level:
        level += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end] + '\n'


set_mctrl = function(driver, 'qcom_geni_serial_set_mctrl')
termios = function(driver, 'qcom_geni_serial_set_termios')
update = function(core, 'uart_update_mctrl')
ttyport_flow = function(serdev, 'ttyport_set_flow_control')
anchor = '\ttrace_geni_serial_set_termios(uport->dev,'
assert termios.count(anchor) == 1
assert termios.count('\t\tport->manual_flow = false;') == 1
assert termios.count('\t\tport->manual_flow = true;') == 1
candidate = termios.replace('\n\t\tport->manual_flow = false;', '').replace(
    '\n\t\tport->manual_flow = true;', '')
candidate = candidate.replace(anchor, '''\t/* Reapply RTS after changing mode even when the cached mctrl is unchanged.
\t * Serialize the mode and RFR register with normal modem-control updates.
\t */
\tscoped_guard(uart_port_lock_irqsave, uport) {
\t\tport->manual_flow = !(termios->c_cflag & CRTSCTS);
\t\tif (!(uport->rs485.flags & SER_RS485_ENABLED))
\t\t\tqcom_geni_serial_set_mctrl(uport, uport->mctrl);
\t}

''' + anchor)
patched = driver.replace(termios, candidate)
patch = ''.join(difflib.unified_diff(driver.splitlines(True), patched.splitlines(True),
    fromfile='a/drivers/tty/serial/qcom_geni_serial.c',
    tofile='b/drivers/tty/serial/qcom_geni_serial.c'))
(R / 'geni-rts-mode-lock-candidate.patch').write_text(patch)

# Reuse the exact host API prefix and macro dependency extraction from 234.
old_test = ast.parse((R.parent / 'kernel234/test-rts-mode-contract.py').read_text())
prefix = next(ast.literal_eval(n.value) for n in old_test.body
              if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'prefix' for t in n.targets))
prefix = prefix.replace('#define guard(name) fake_guard', '')
prefix = prefix.replace('bool suspended;', 'bool suspended, console;')
prefix = prefix.replace('static void fake_guard(struct uart_port *p) { (void)p; }', '')
prefix = prefix.replace('static bool uart_console(struct uart_port *p) { (void)p; return false; }',
                        'static bool uart_console(struct uart_port *p) { return p->console; }')
prefix = prefix.replace('static void writel(u32 v,void *p) { memcpy(p,&v,sizeof(v)); }', '')
prefix = prefix.replace('static int set_rate(struct fake_se *p,unsigned int b) { (void)p;(void)b;return 0; }', '')
extra = r'''
#include <assert.h>
static struct uart_port *active;
static unsigned lock_depth, irq_disabled, lock_errors, rfr_writes, guard_entries;
static int rate_error, interrupt_rts;
static void uart_update_mctrl(struct uart_port *,unsigned int,unsigned int);
struct lock_guard { unsigned saved_irq; bool held; };
static struct lock_guard fake_lock(struct uart_port *p) {
 assert(p==active && !lock_depth);struct lock_guard g={irq_disabled,true};
 lock_depth++;irq_disabled=1;guard_entries++;return g;
}
static void fake_unlock(struct lock_guard *g) {
 if(!g->held)return;
 assert(lock_depth==1 && irq_disabled);lock_depth--;irq_disabled=g->saved_irq;g->held=false;
}
#define guard(name) struct lock_guard __guard __attribute__((cleanup(fake_unlock))) = fake_lock
#define scoped_guard(name,p) for(struct lock_guard __guard __attribute__((cleanup(fake_unlock)))=fake_lock(p);__guard.held;fake_unlock(&__guard))
static int set_rate(struct fake_se *p,unsigned int b) {
 (void)p;(void)b;assert(!lock_depth);
 if(interrupt_rts>=0)uart_update_mctrl(active,interrupt_rts?TIOCM_RTS:0,interrupt_rts?0:TIOCM_RTS);
 return rate_error;
}
'''

defs = {}
lines = driver.splitlines()
i = 0
while i < len(lines):
    line = lines[i]
    if line.startswith('#define '):
        body = line
        while body.rstrip().endswith('\\'):
            i += 1
            body += '\n' + lines[i]
        defs[re.match(r'#define\s+(\w+)', body)[1]] = body
    i += 1
needed = set(re.findall(r'\b[A-Z][A-Z0-9_]+\b', set_mctrl + termios))
selected = {}
while True:
    new = {name: body for name, body in defs.items() if name in needed and name not in selected}
    if not new:
        break
    selected.update(new)
    needed.update(re.findall(r'\b[A-Z][A-Z0-9_]+\b', '\n'.join(new.values())))

mmio = r'''
static void writel(u32 v,void *p) {
 assert(active);
 if(p==active->membase+SE_UART_MANUAL_RFR) {
  rfr_writes++;if(lock_depth!=1||!irq_disabled)lock_errors++;
 }
 memcpy(p,&v,sizeof(v));
}
'''
serdev_prefix = r'''
struct tty_struct { struct ktermios termios; struct uart_port *port; };
struct serport { struct tty_struct *tty; };
struct serdev_controller { struct serport *serport; };
static struct serport *serdev_controller_get_drvdata(struct serdev_controller *c) { return c->serport; }
static int tty_set_termios(struct tty_struct *tty,struct ktermios *t) {
 struct ktermios old=tty->termios;
 qcom_geni_serial_set_termios(tty->port,t,&old);tty->termios=*t;return 0;
}
'''
tests = r'''
static unsigned cases,mismatches,exclusions,failed_rate,serdev_cases,interleavings;
static u32 regs[1024];static struct qcom_geni_serial_port p;
static const struct uart_ops ops={qcom_geni_serial_set_mctrl};
static const struct fake_data data={set_rate};
static void reset(unsigned before,unsigned rts,unsigned suspended,unsigned console,unsigned rs485) {
 assert(!lock_depth && !irq_disabled);memset(regs,0,sizeof(regs));memset(&p,0,sizeof(p));
 p.uport.mctrl=TIOCM_DTR|(rts?TIOCM_RTS:0);p.uport.suspended=suspended;p.uport.console=console;
 p.uport.rs485.flags=rs485?SER_RS485_ENABLED:0;p.uport.ops=&ops;p.uport.membase=(unsigned char *)regs;
 p.dev_data=&data;p.tx_fifo_depth=16;p.manual_flow=before;active=&p.uport;
 rate_error=0;interrupt_rts=-1;
 {guard(uart_port_lock_irqsave)(&p.uport);qcom_geni_serial_set_mctrl(&p.uport,p.uport.mctrl);}
}
static void change(unsigned manual) {
 struct ktermios t={.c_cflag=CS8|(manual?0:CRTSCTS)};
 qcom_geni_serial_set_termios(&p.uport,&t,&t);
 assert(!lock_depth && !irq_disabled);cases++;
}
static void check(unsigned manual) {
 u32 expected=(manual&&!(p.uport.mctrl&TIOCM_RTS)&&!p.uport.suspended)?UART_MANUAL_RFR_EN|UART_RFR_NOT_READY:0;
 if(readl(p.uport.membase+SE_UART_MANUAL_RFR)!=expected)mismatches++;
}
int main(void) {
 for(unsigned before=0;before<2;before++)for(unsigned after=0;after<2;after++)
 for(unsigned rts=0;rts<2;rts++)for(unsigned suspended=0;suspended<2;suspended++) {
  reset(before,rts,suspended,0,0);change(after);
  uart_update_mctrl(&p.uport,rts?TIOCM_RTS:0,rts?0:TIOCM_RTS);check(after);
 }
 unsigned base_mismatches=mismatches;
 for(unsigned console=0;console<2;console++)for(unsigned rs485=0;rs485<2;rs485++) {
  if(!console&&!rs485)continue;
  reset(0,0,0,console,rs485);u32 sentry=0xa5a5;memcpy(p.uport.membase+SE_UART_MANUAL_RFR,&sentry,4);
  unsigned writes=rfr_writes;change(1);change(0);
  if(rfr_writes!=writes||readl(p.uport.membase+SE_UART_MANUAL_RFR)!=sentry)exclusions++;
 }
 for(unsigned before=0;before<2;before++) {
  reset(before,0,0,0,0);unsigned writes=rfr_writes;rate_error=-5;change(!before);
  if(p.manual_flow!=before||rfr_writes!=writes)failed_rate++;
 }
 // The requested modem-control bit may change before the short critical section.
 for(unsigned after=0;after<2;after++)for(unsigned rts=0;rts<2;rts++) {
  reset(!after,!rts,0,0,0);interrupt_rts=rts;change(after);check(after);interleavings++;
 }
 // Actual serdev ttyport flow-control implementation; same cached RTS follows it.
 for(unsigned before=0;before<2;before++)for(unsigned enable=0;enable<2;enable++)
 for(unsigned rts=0;rts<2;rts++) {
  reset(before,rts,0,0,0);
  struct tty_struct tty={.termios={.c_cflag=CS8|(before?0:CRTSCTS)},.port=&p.uport};
  struct serport sp={&tty};struct serdev_controller ctrl={&sp};
  ttyport_set_flow_control(&ctrl,enable);uart_update_mctrl(&p.uport,rts?TIOCM_RTS:0,rts?0:TIOCM_RTS);
  check(!enable);serdev_cases++;
 }
 // IRQ state is restored even when the caller already has IRQs disabled.
 reset(0,0,0,0,0);irq_disabled=1;
 struct ktermios t={.c_cflag=CS8};qcom_geni_serial_set_termios(&p.uport,&t,&t);
 assert(irq_disabled==1&&!lock_depth);irq_disabled=0;check(1);
 printf("{\"base_cases\":16,\"base_mismatches\":%u,\"all_mode_mismatches\":%u,\"lock_irq_violations\":%u,\"console_rs485_violations\":%u,\"failed_rate_violations\":%u,\"serdev_cases\":%u,\"controlled_interleavings\":%u,\"termios_cases\":%u,\"guard_entries\":%u}\n",base_mismatches,mismatches,lock_errors,exclusions,failed_rate,serdev_cases,interleavings,cases,guard_entries);
 return 0;
}
'''
variants = {
    'current': termios,
    'rejected_naked_sync': termios.replace(anchor, '\tqcom_geni_serial_set_mctrl(uport, uport->mctrl);\n\n' + anchor),
    'locked_candidate': candidate,
}
results = {}
out = Path('/mnt/e/edk2-samurai-out/bluetooth-transport-20261023/test-output')
out.mkdir(parents=True, exist_ok=True)
for name, body in variants.items():
    c = out / (name + '.c')
    c.write_text(prefix + extra + '\n'.join(selected.values()) + '\n' + mmio + set_mctrl + update + body + serdev_prefix + ttyport_flow + tests)
    binary = out / name
    cp = subprocess.run(['gcc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-O1', '-g',
        '-fsanitize=address,undefined', '-fno-omit-frame-pointer', str(c), '-o', str(binary)], capture_output=True)
    (out / (name + '-build.log')).write_bytes(cp.stdout + cp.stderr)
    assert cp.returncode == 0, cp.stderr.decode()
    run = subprocess.run([str(binary)], capture_output=True)
    (out / (name + '-run.log')).write_bytes(run.stdout + run.stderr)
    assert run.returncode == 0 and not run.stderr, (name, run.stdout, run.stderr)
    results[name] = json.loads(run.stdout)
assert results['current']['base_mismatches'] == 2
assert results['rejected_naked_sync']['base_mismatches'] == 0
assert results['rejected_naked_sync']['lock_irq_violations'] > 0
assert results['rejected_naked_sync']['console_rs485_violations'] > 0
for field in ['all_mode_mismatches', 'lock_irq_violations', 'console_rs485_violations', 'failed_rate_violations']:
    assert results['locked_candidate'][field] == 0, field
report = dict(results=results, asan_ubsan_passed=True,
    real_geni_core_and_serdev_functions_extracted=True,
    lock_irq_and_mmio_apis_modeled=True, kernel_lockdep_not_run=True,
    real_kernel_or_handset_not_built_or_changed=True,
    historical_phase5_causality_not_established=True,
    source_geni_sha256=hashlib.sha256(driver.encode()).hexdigest(),
    patch_sha256=hashlib.sha256(patch.encode()).hexdigest())
(R / 'rts-contract-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))

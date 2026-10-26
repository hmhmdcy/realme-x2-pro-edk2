"""Minimal late-producer teardown repair; never modify the frozen R1."""
from pathlib import Path
import difflib
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
R1 = HERE.parent / 'eud-runtime-window-candidate'
AUDIT = HERE.parents[1] / 'charging-oem-audit-20261023'
REVIEW = AUDIT / 'eud-runtime-window-review/late-remove-counterexample'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(R1 / 'eud.c') == '8cdd661b7834a7ccba46bd7577be84bd3bb81f6a00fb512d2b70e9d7c4c1231c'
assert sha(R1 / '0001-eud-optional-software-window.patch') == '838cb462b1ff1535185b82fee980ef7f368585ba975aaf3f394e07f5e93f4929'
review = json.loads((REVIEW / 'result.json').read_text())
assert review['case']['reproduced'] and review['case']['late_rx_pending_after_remove']
for name, digest in review['files'].items():
    assert sha(REVIEW / name) == digest
old = (R1 / 'eud.c').read_text()
before = '''        uart_remove_one_port(&eud_uart_driver, port);
        if (borrowed)
                cancel_work_sync(&up->tx_work);'''
after = '''        uart_remove_one_port(&eud_uart_driver, port);
        /* unregister_console and UART removal have now joined every producer.
         * A callback that passed its gate before stopping may have queued RX
         * or TX after the early cancellations. Join both one final time before
         * mappings/global state can be released, for borrowed and normal exit.
         */
        cancel_delayed_work_sync(&up->rx_work);
        cancel_work_sync(&up->tx_work);'''
assert old.count(before) == 1
new = old.replace(before, after)
(HERE / 'eud.c').write_bytes(new.encode())
(HERE / 'eud-com-window.h').write_bytes((R1 / 'eud-com-window.h').read_bytes())
(HERE / 'build-object.py').write_bytes((R1 / 'build-object.py').read_bytes())
base = (AUDIT / 'apsd-integration/current-r7/snapshots/drivers--tty--serial--eud.c').read_text()
patch = ''.join(difflib.unified_diff(base.splitlines(True), new.splitlines(True),
              fromfile='a/drivers/tty/serial/eud.c', tofile='b/drivers/tty/serial/eud.c'))
header = (HERE / 'eud-com-window.h').read_text()
patch += ''.join(difflib.unified_diff([], header.splitlines(True),
              fromfile='/dev/null', tofile='b/drivers/tty/serial/eud-com-window.h'))
(HERE / 'eud-window-r2.patch').write_bytes(patch.encode())
delta = ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
              fromfile='r1/eud.c', tofile='r2/eud.c'))
(HERE / 'r1-to-r2.patch').write_bytes(delta.encode())


def body(text, name):
    match = re.search(r'^static void ' + name + r'\([^;]*?\)\n\{', text, re.M)
    assert match, name
    return text[match.start():text.index('\n}', match.end()) + 2]


old_body, new_body = body(old, 'eud_remove_locked'), body(new, 'eud_remove_locked')
fixture = (R1 / 'candidate-functions.inc').read_text()
assert fixture.count(old_body) == 1
(HERE / 'candidate-functions.inc').write_bytes(fixture.replace(old_body, new_body).encode())
for name in ['nbcon-functions.inc', 'fake-eud-os.h']:
    (HERE / name).write_bytes((REVIEW / name).read_bytes())
fake = (HERE / 'fake-eud-os.h').read_text()
fake = fake.replace('static void schedule_work(struct work_struct *p) { p->pending = 1; schedules++; }',
    'static void (*review_schedule_hook)(void);\nstatic void schedule_work(struct work_struct *p) { if(review_schedule_hook)review_schedule_hook(); p->pending = 1; schedules++; }')
fake = fake.replace('static void uart_remove_one_port(void *d, struct uart_port *p) { assert(!port_depth); uart_removes++; }',
    'static void (*review_uart_remove_hook)(void);\nstatic void uart_remove_one_port(void *d, struct uart_port *p) { assert(!port_depth); uart_removes++; if(review_uart_remove_hook)review_uart_remove_hook(); }')
(HERE / 'fake-eud-os.h').write_bytes(fake.encode())
# Reuse only fixture helpers, not the old main or any original test suite.
prefix = (REVIEW / 'test-late-remove.c').read_text().split('static pthread_t late_console_thread;', 1)[0]
prefix += r'''
static pthread_t producer;
static void finish_producer(void) { release_writer();pthread_join(producer,NULL); }
static void *review_atomic(void *unused) {
 struct nbcon_write_context ctx={"log",3};review_writer=true;
 eud_console_write_atomic(NULL,&ctx);return NULL;
}
static void *review_start_tx(void *unused) { review_writer=true;eud_start_tx(&up.port);return NULL; }
static void start_case(void *(*entry)(void *),bool tty) {
 clear();reset_review();up.console_registered=true;
 review_unregister_hook=NULL;review_uart_remove_hook=NULL;review_schedule_hook=NULL;
 registers[EUD_REG_INT_STATUS_1/sizeof(u32)]=EUD_INT_RX_PENDING;
 if(tty)review_schedule_hook=pause_here;else review_mod_hook=pause_here;
 assert(!pthread_create(&producer,NULL,entry,NULL));wait_for(&review_paused);
}
static void finish_case(const char *name) {
 assert(!eud&&!device.dev.data&&!up.rx_work.work.pending&&!up.tx_work.pending);
 assert(!review_tx_running);printf("ok: %s\n",name);
}
int main(void) {
 start_case(review_legacy,false);quiet();u64 cookie=r.cookie;
 assert(!up.rx_work.work.pending);review_unregister_hook=finish_producer;
 eud_remove(&device);
 assert(up.window_state==EUD_COM_REMOVED&&eud_window_orphan==cookie&&ahb==0x11);
 finish_case("borrowed legacy late RX joined after unregister and UART removal");

 start_case(review_atomic,false);review_unregister_hook=finish_producer;
 eud_remove(&device);assert(ahb==0x77);
 finish_case("ordinary atomic late RX joined after unregister");

 start_case(review_console,false);review_unregister_hook=finish_producer;
 eud_remove(&device);assert(ahb==0x77);
 finish_case("ordinary threaded nbcon late RX joined after unregister");

 start_case(review_start_tx,true);review_uart_remove_hook=finish_producer;
 eud_remove(&device);assert(ahb==0x77);
 finish_case("ordinary late TTY start_tx joined after UART producer removal");
 return 0;
}
'''
(HERE / 'test-late-producers.c').write_bytes(prefix.encode())
result = {'revision': 2, 'base_r1_sha256': sha(R1 / 'eud.c'),
          'base_r1_test_receipt_sha256': sha(R1 / 'candidate-test-result.json'),
          'r1_failure_receipt_sha256': sha(REVIEW / 'result.json'),
          'candidate_sha256': sha(HERE / 'eud.c'), 'header_sha256': sha(HERE / 'eud-com-window.h'),
          'patch_sha256': sha(HERE / 'eud-window-r2.patch'), 'delta_sha256': sha(HERE / 'r1-to-r2.patch'),
          'only_changed_function': 'eud_remove_locked',
          'remaining_r1_function_fixture_bytes_unchanged': fixture.replace(old_body, '') ==
              (HERE / 'candidate-functions.inc').read_text().replace(new_body, ''),
          'r1_modified': False, 'old_9_groups_rerun': False}
(HERE / 'candidate-result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
print(json.dumps(result, indent=2))

#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include "samurai-sensor-power-seq.h"
struct mock { int refs[2], calls[2], delays; unsigned fail_enable, fail_disable; };
static int enable(void *ctx, enum samurai_sensor_rail r) {
    struct mock *m = ctx; m->calls[r]++;
    if (m->fail_enable & (1U << r)) return -10-r;
    assert(m->refs[r] == 0); m->refs[r]++; return 0;
}
static int disable(void *ctx, enum samurai_sensor_rail r) {
    struct mock *m = ctx;
    if (m->fail_disable & (1U << r)) return -20-r;
    assert(m->refs[r] == 1); m->refs[r]--; return 0;
}
static void delay(void *ctx) { ((struct mock *)ctx)->delays++; }
static const struct samurai_power_ops ops = { enable, disable, delay };
static void invariant(struct samurai_power_state *s, struct mock *m) {
    assert(m->refs[0] == s->vdd_on && m->refs[1] == s->io_on);
    assert(!s->io_on || s->vdd_on);
}
int main(void) {
    for (unsigned en = 0; en < 4; en++) for (unsigned dis = 0; dis < 4; dis++) {
        struct mock m = { .fail_enable=en, .fail_disable=dis };
        struct samurai_power_state s = {0};
        int ret = samurai_power_on(&s, &ops, &m);
        assert((ret == 0) == (en == 0)); invariant(&s, &m);
        if (!en) {
            assert(!samurai_power_on(&s, &ops, &m));
            assert(m.calls[0] == 1 && m.calls[1] == 1 && m.delays == 1);
            (void)samurai_power_off(&s, &ops, &m); invariant(&s, &m);
        }
        m.fail_enable = m.fail_disable = 0;
        assert(!samurai_power_on(&s, &ops, &m)); invariant(&s, &m);
        assert(!samurai_power_off(&s, &ops, &m)); invariant(&s, &m);
        assert(!samurai_power_off(&s, &ops, &m)); invariant(&s, &m);
        assert(!s.vdd_on && !s.io_on);
    }
    puts("PASS: actual supply sequence, delay, enable/disable failures, rollback retry and reference balance");
}

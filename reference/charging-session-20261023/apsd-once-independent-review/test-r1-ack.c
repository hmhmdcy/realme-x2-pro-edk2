#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "samurai-apsd-once-r1.h"

static struct samurai_apsd_once writing(void)
{
    struct samurai_apsd_once s = { 0 };
    assert(!samurai_apsd_attach(&s, 0));
    assert(samurai_apsd_sample(&s, s.epoch, 1, 1, 1, 1) == SAMURAI_APSD_REQUEST);
    assert(!samurai_apsd_claim(&s, s.epoch, 2, 10));
    return s;
}

int main(void)
{
    struct samurai_apsd_once s = writing();
    int ret = samurai_apsd_write_done(&s, s.epoch, 11, -EREMOTEIO);
    assert(ret == -ETIMEDOUT && s.error == -ETIMEDOUT && s.attempted);
    assert(samurai_apsd_claim(&s, s.epoch, 12, 20) == -ETIMEDOUT);
    printf("late_bus_error=%d stored_primary=%d no_retry=true\n", -EREMOTEIO, s.error);
    s = writing();
    assert(samurai_apsd_cancel(&s, s.epoch) == -ECANCELED);
    assert(samurai_apsd_write_done(&s, s.epoch, 3, -ENXIO) == -ECANCELED);
    assert(s.error == -ECANCELED && s.attempted);
    printf("cancelled_late_bus_error=%d stored_primary=%d\n", -ENXIO, s.error);
    s = writing();
    unsigned long long old = s.epoch;
    samurai_apsd_detach(&s);
    assert(!samurai_apsd_attach(&s, 3));
    struct samurai_apsd_once before = s;
    assert(samurai_apsd_write_done(&s, old, 4, -EIO) == -ESTALE);
    assert(!memcmp(&before, &s, sizeof(s)));
    puts("old_epoch_late_error_rejected_without_mutating_new_session=true");
    return 0;
}

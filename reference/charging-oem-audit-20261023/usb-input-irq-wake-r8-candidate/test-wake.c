/* Actual source functions with only kernel-facing APIs modeled. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>

#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))
#define BIT(n) (1UL << (n))
#define EPROBE_DEFER 517
#define IRQF_ONESHOT 1
#define IRQ_HANDLED 1

typedef int irqreturn_t;
struct device { void *data; bool wake; };
struct platform_device { struct device dev; };
struct mutex { bool held; };
struct delayed_work { int unused; };
struct power_supply { struct device dev; void *data; };
struct samurai_usb_input {
	struct device *event_dev;
	int event_irqs[2];
	unsigned long wake_armed;
	struct power_supply *psy;
	struct mutex lock;
	struct delayed_work work;
	bool udc_valid;
	bool paused;
};

static struct samurai_usb_input input;
static struct platform_device pdev;
static struct power_supply supply;
static void *system_wq = (void *)1;
static int queued, cancelled, warned, requested;
static int enable_error, disable_error, request_error_at;
static int irq_refs[224], operations[64][2], operation_count;
static int mock_irqs[2];
static bool fire_probe_irq;
static irqreturn_t samurai_usb_event(int irq, void *data);

static void mutex_lock(struct mutex *lock)
{
	assert(!lock->held);
	lock->held = true;
}

static void mutex_unlock(struct mutex *lock)
{
	assert(lock->held);
	lock->held = false;
}

static void *dev_get_drvdata(struct device *dev)
{
	return dev->data;
}

static void *platform_get_drvdata(struct platform_device *dev)
{
	return dev->dev.data;
}

static bool device_may_wakeup(struct device *dev)
{
	return dev->wake;
}

static void cancel_delayed_work_sync(struct delayed_work *work)
{
	assert(work == &input.work && input.paused && !input.udc_valid);
	assert(!input.lock.held);
	cancelled++;
}

static int mod_delayed_work(void *queue, struct delayed_work *work,
			    unsigned long delay)
{
	assert(queue == system_wq && work == &input.work && delay == 0);
	assert(!input.paused);
	queued++;
	return 0;
}

static void dev_warn(struct device *dev, const char *format, ...)
{
	assert(dev == &pdev.dev);
	(void)format;
	warned++;
}

static int enable_irq_wake(int irq)
{
	assert(irq == 221 || irq == 222);
	assert(operation_count < 64);
	operations[operation_count][0] = irq;
	operations[operation_count++][1] = 1;
	if (irq == enable_error)
		return -EIO;
	assert(!irq_refs[irq]);
	irq_refs[irq]++;
	return 0;
}

static int disable_irq_wake(int irq)
{
	assert(irq == 221 || irq == 222);
	assert(operation_count < 64);
	operations[operation_count][0] = irq;
	operations[operation_count++][1] = 0;
	assert(irq_refs[irq]);
	if (irq == disable_error)
		return -EAGAIN;
	irq_refs[irq]--;
	return 0;
}

static int platform_get_irq_byname_optional(struct platform_device *dev,
					    const char *name)
{
	assert(dev == &pdev);
	if (!strcmp(name, "usbin-plugin"))
		return mock_irqs[0];
	assert(!strcmp(name, "usbin-src-change"));
	return mock_irqs[1];
}

static int devm_request_threaded_irq(struct device *dev, int irq, void *top,
				     irqreturn_t (*thread)(int, void *),
				     unsigned long flags, const char *name,
				     void *data)
{
	assert(dev == &pdev.dev && top == NULL && thread == samurai_usb_event);
	assert(flags == IRQF_ONESHOT && data == &input);
	assert((!strcmp(name, "usbin-plugin") && irq == 221) ||
	       (!strcmp(name, "usbin-src-change") && irq == 222));
	requested++;
	if (requested == request_error_at)
		return -EIO;
	if (fire_probe_irq)
		assert(thread(irq, data) == IRQ_HANDLED);
	return 0;
}

#include "actual-functions.inc"

static void reset(void)
{
	memset(&input, 0, sizeof(input));
	memset(irq_refs, 0, sizeof(irq_refs));
	memset(operations, 0, sizeof(operations));
	supply.data = &input;
	supply.dev.wake = true;
	input.psy = &supply;
	input.event_dev = &pdev.dev;
	input.event_irqs[0] = 221;
	input.event_irqs[1] = 222;
	input.udc_valid = true;
	pdev.dev.data = &input;
	queued = cancelled = warned = requested = 0;
	enable_error = disable_error = request_error_at = operation_count = 0;
	fire_probe_irq = false;
	mock_irqs[0] = 221;
	mock_irqs[1] = 222;
}

static void cleared(void)
{
	assert(!input.wake_armed);
	assert(!irq_refs[221] && !irq_refs[222]);
}

int main(void)
{
	int groups = 0;
	int count;

	reset();
	input.event_irqs[0] = input.event_irqs[1] = 0;
	input.psy = NULL;
	input.paused = true;
	fire_probe_irq = true;
	assert(samurai_usb_request_events(&pdev, &input) == 0);
	assert(requested == 2 && input.event_irqs[0] == 221 &&
	       input.event_irqs[1] == 222 && queued == 0);
	cleared();

	reset();
	input.event_irqs[0] = input.event_irqs[1] = 0;
	input.psy = NULL;
	input.paused = true;
	request_error_at = 2;
	assert(samurai_usb_request_events(&pdev, &input) == -EIO);
	assert(input.event_irqs[0] == 221 && input.event_irqs[1] == 0);
	samurai_usb_cleanup_wake(&input);
	cleared();
	groups++;

	reset();
	input.event_irqs[0] = input.event_irqs[1] = 0;
	mock_irqs[0] = -ENXIO;
	mock_irqs[1] = -ENODEV;
	assert(samurai_usb_request_events(&pdev, &input) == 0 && requested == 0);
	assert(samurai_usb_suspend(&pdev.dev) == 0);
	assert(samurai_usb_resume(&pdev.dev) == 0 && operation_count == 0);
	cleared();
	groups++;

	reset();
	mock_irqs[1] = -ENXIO;
	assert(samurai_usb_request_events(&pdev, &input) == -ENXIO);
	reset();
	mock_irqs[0] = mock_irqs[1] = 221;
	assert(samurai_usb_request_events(&pdev, &input) == -EINVAL);
	groups++;

	reset();
	supply.dev.wake = false;
	assert(samurai_usb_suspend(&pdev.dev) == 0 && input.paused);
	assert(cancelled == 1 && operation_count == 0);
	assert(samurai_usb_resume(&pdev.dev) == 0 && !input.paused && queued == 1);
	cleared();
	groups++;

	reset();
	assert(samurai_usb_suspend(&pdev.dev) == 0);
	assert(input.paused && input.wake_armed == 3);
	assert(irq_refs[221] == 1 && irq_refs[222] == 1);
	assert(samurai_usb_resume(&pdev.dev) == 0);
	assert(!input.paused && !input.udc_valid && queued == 1);
	cleared();
	assert(operation_count == 4);
	assert(operations[0][0] == 221 && operations[0][1] == 1);
	assert(operations[1][0] == 222 && operations[1][1] == 1);
	assert(operations[2][0] == 222 && operations[2][1] == 0);
	assert(operations[3][0] == 221 && operations[3][1] == 0);
	groups++;

	reset();
	enable_error = 221;
	assert(samurai_usb_suspend(&pdev.dev) == -EIO);
	assert(!input.paused && queued == 1 && cancelled == 1);
	cleared();
	groups++;

	reset();
	enable_error = 222;
	assert(samurai_usb_suspend(&pdev.dev) == -EIO);
	assert(!input.paused && queued == 1 && operation_count == 3);
	assert(operations[2][0] == 221 && operations[2][1] == 0);
	cleared();
	groups++;

	reset();
	enable_error = 222;
	disable_error = 221;
	assert(samurai_usb_suspend(&pdev.dev) == -EIO);
	assert(input.wake_armed == 1 && warned == 1 && !input.paused);
	count = operation_count;
	input.udc_valid = true;
	assert(samurai_usb_suspend(&pdev.dev) == -EAGAIN);
	assert(cancelled == 1 && input.udc_valid && operation_count == count + 1);
	disable_error = 0;
	samurai_usb_cleanup_wake(&input);
	cleared();
	groups++;

	reset();
	input.paused = true;
	assert(samurai_usb_event(221, &input) == IRQ_HANDLED && queued == 0);
	input.paused = false;
	assert(samurai_usb_event(221, &input) == IRQ_HANDLED && queued == 1);
	groups++;

	reset();
	assert(samurai_usb_suspend(&pdev.dev) == 0);
	supply.dev.wake = false;
	input.psy = NULL;
	samurai_usb_shutdown(&pdev);
	assert(input.paused && cancelled == 2 && !warned);
	cleared();
	groups++;

	assert(groups == 10);
	puts("10 IRQ wake lifecycle groups passed with actual source functions");
	return 0;
}

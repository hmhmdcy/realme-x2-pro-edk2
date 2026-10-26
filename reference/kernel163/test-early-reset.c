#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define EPROBE_DEFER 517
#define GPIO_ACTIVE_LOW 1
#define GPIOD_ASIS 0
#define IS_ERR(value) ((intptr_t)(value) < 0)
#define PTR_ERR(value) ((int)(intptr_t)(value))
struct device_node { int refs; bool available; };
struct device { struct device_node *of_node; };
struct platform_device { struct device dev; };
struct of_phandle_args { struct device_node *np; int args_count; unsigned int args[2]; };
struct gpio_desc { bool claimed; };
static struct device_node controller, other_controller, panel_node;
static struct gpio_desc descriptor;
static int sm8150_pinctrl;
static int scenario, parse_calls, gpio_gets, gpio_puts, directions, warnings, messages;
static int physical_level, logical_output, parent_calls;
static bool controller_ready;
static char actions[32];
static unsigned int action_count;
static void action(char value) { actions[action_count++] = value; actions[action_count] = 0; }
static bool of_machine_is_compatible(const char *compatible)
{
	assert(!strcmp(compatible, "realme,samurai"));
	return scenario != 2;
}
static struct device_node *of_find_compatible_node(void *from, void *type, const char *compatible)
{
	assert(!from && !type && !strcmp(compatible, "samsung,sofef03f-m"));
	if (scenario == 3) return NULL;
	panel_node.refs++;
	return &panel_node;
}
static bool of_device_is_available(struct device_node *node) { return node->available; }
static void of_node_put(struct device_node *node) { assert(node->refs > 0); node->refs--; }
static int of_parse_phandle_with_args(struct device_node *node, const char *name,
				      const char *cells, int index, struct of_phandle_args *args)
{
	assert(node == &panel_node && !strcmp(name, "reset-gpios") && !strcmp(cells, "#gpio-cells") && index == 0);
	parse_calls++;
	if (scenario == 6) return -EINVAL;
	args->np = scenario == 7 ? &other_controller : &controller;
	args->np->refs++;
	args->args_count = scenario == 8 ? 1 : 2;
	args->args[0] = scenario == 9 ? 25 : 6;
	args->args[1] = scenario == 10 ? 0 : GPIO_ACTIVE_LOW;
	return 0;
}
static struct device_node *of_fwnode_handle(struct device_node *node) { return node; }
static struct gpio_desc *fwnode_gpiod_get_index(struct device_node *node, const char *name,
					      int index, int flags, const char *label)
{
	assert(controller_ready && node == &panel_node && !strcmp(name, "reset") && index == 0);
	assert(flags == GPIOD_ASIS && !strcmp(label, "samurai-boot-panel"));
	gpio_gets++;
	if (scenario == 11) return (void *)(intptr_t)-EPROBE_DEFER;
	if (scenario == 12) return (void *)(intptr_t)-EBUSY;
	assert(!descriptor.claimed);
	descriptor.claimed = true;
	action('G');
	return &descriptor;
}
static int gpiod_direction_output(struct gpio_desc *gpio, int value)
{
	assert(gpio == &descriptor && gpio->claimed && value == 1);
	directions++;
	logical_output = value;
	action('D');
	if (scenario == 13) return -EIO;
	physical_level = !value;
	return 0;
}
static void gpiod_put(struct gpio_desc *gpio)
{
	assert(gpio == &descriptor && gpio->claimed);
	gpio_puts++;
	gpio->claimed = false;
	action('R');
}
static void dev_info(struct device *dev, const char *format)
{
	assert(dev->of_node == &controller && strstr(format, "boot reset asserted"));
	messages++;
}
static void dev_warn(struct device *dev, const char *format, int error)
{
	assert(dev->of_node == &controller && strstr(format, "boot reset unavailable") && error < 0);
	warnings++;
}
static int msm_pinctrl_probe(struct platform_device *pdev, int *data)
{
	assert(pdev->dev.of_node == &controller && data == &sm8150_pinctrl);
	parent_calls++;
	if (scenario == 5) return -ENOMEM;
	controller_ready = true;
	action('C');
	return 0;
}

/* ACTUAL_FUNCTIONS */

int main(void)
{
	for (scenario = 0; scenario < 14; scenario++) {
		struct platform_device pdev = { .dev.of_node = &controller };
		controller = (struct device_node){ 0 };
		other_controller = (struct device_node){ 0 };
		panel_node = (struct device_node){ .available = scenario != 4 };
		descriptor = (struct gpio_desc){ 0 };
		parse_calls = gpio_gets = gpio_puts = directions = warnings = messages = parent_calls = 0;
		logical_output = -1;
		physical_level = scenario == 1 ? 0 : 1;
		controller_ready = false;
		action_count = 0;
		actions[0] = 0;
		int result = sm8150_pinctrl_probe(&pdev);
		assert(result == (scenario == 5 ? -ENOMEM : 0));
		assert(parent_calls == 1 && !controller.refs && !other_controller.refs && !panel_node.refs);
		assert(!descriptor.claimed);
		if (scenario < 2) {
			assert(physical_level == 0 && logical_output == 1 && directions == 1);
			assert(gpio_gets == 1 && gpio_puts == 1 && messages == 1 && warnings == 0);
			assert(!strcmp(actions, "CGDR"));
			/* The native panel can acquire the released descriptor without changing the held level. */
			struct gpio_desc *native = fwnode_gpiod_get_index(&panel_node, "reset", 0, GPIOD_ASIS, "samurai-boot-panel");
			assert(!IS_ERR(native) && physical_level == 0);
			gpiod_put(native);
		} else if (scenario <= 5) {
			assert(!gpio_gets && !directions && !warnings && !messages && !parse_calls);
		} else if (scenario <= 10) {
			assert(!gpio_gets && !directions && warnings == 1 && !messages && parse_calls == 1);
		} else if (scenario <= 12) {
			assert(gpio_gets == 1 && !directions && !gpio_puts && warnings == 1 && !messages);
		} else {
			assert(directions == 1 && gpio_puts == 1 && physical_level == 1 && warnings == 1 && !messages);
		}
	}
	printf("14 actual-function scenarios passed\n");
	return 0;
}

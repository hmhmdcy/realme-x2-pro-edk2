#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define IN
#define OUT
#define STATIC static
#define VOID void
#define EFIAPI
typedef uint8_t BOOLEAN;
typedef uint8_t UINT8;
typedef uint16_t UINT16;
typedef uint32_t UINT32;
typedef uint64_t UINT64;
typedef uint64_t EFI_STATUS;
typedef void *EFI_EVENT;
typedef struct { UINT32 Data1; UINT16 Data2, Data3; UINT8 Data4[8]; } EFI_GUID;
#define TRUE 1
#define FALSE 0
#define EFI_SUCCESS 0
#define EFI_UNSUPPORTED (UINT64_C(1) << 63 | 3)
#define EFI_DEVICE_ERROR (UINT64_C(1) << 63 | 7)
#define EFI_NOT_FOUND (UINT64_C(1) << 63 | 14)
#define EFI_NOT_READY (UINT64_C(1) << 63 | 6)
#define EFI_ERROR(status) ((status) >> 63)
#define EVT_NOTIFY_SIGNAL 0x200
#define TPL_CALLBACK 8
#define DEBUG_INFO 0x40
#define DEBUG_WARN 2
#define ZeroMem(ptr, size) memset(ptr, 0, size)
#define DEBUG(args) debug_message args

#include "Protocol/EFITlmm.h"
EFI_GUID gQcomTlmmProtocolGuid = QCOM_TLMM_PROTOCOL_GUID;
EFI_GUID gEfiEventBeforeExitBootServicesGuid = { .Data1=0x8be0e274 };
EFI_GUID wrong_exit_group = { .Data1=0x27abf055 };
static int scenario, locate_calls, create_calls, close_calls, config_calls, output_calls, debug_calls;
static int physical_reset_level;
static void (*saved_callback)(EFI_EVENT, void *);
static void *saved_context;
static EFI_EVENT event_token = (void *)(uintptr_t)0x1230;
static EFI_QCOM_TLMM_PROTOCOL protocol;
static EFI_STATUS mock_config(UINT32 value, UINT32 enable)
{
	assert(value == UINT32_C(0x20064060) && enable == TLMM_GPIO_ENABLE);
	config_calls++;
	return scenario == 6 ? EFI_DEVICE_ERROR : EFI_SUCCESS;
}
static EFI_STATUS mock_output(UINT32 value, UINT32 output)
{
	assert(value == UINT32_C(0x20064060) && output == GPIO_LOW_VALUE && config_calls == 1);
	output_calls++;
	if (scenario == 7) return EFI_DEVICE_ERROR;
	physical_reset_level = output;
	return EFI_SUCCESS;
}
static void debug_message(UINT32 level, const char *format, EFI_STATUS status)
{
	(void)status;
	assert(level == DEBUG_INFO || level == DEBUG_WARN);
	assert(strstr(format, "SAMURAI"));
	debug_calls++;
}
static EFI_STATUS mock_locate(EFI_GUID *guid, void *registration, void **result)
{
	assert(guid == &gQcomTlmmProtocolGuid && registration == NULL);
	locate_calls++;
	if (scenario == 1) return EFI_NOT_FOUND;
	*result = &protocol;
	return EFI_SUCCESS;
}
static EFI_STATUS mock_create(UINT32 type, UINT32 tpl, void (*callback)(EFI_EVENT, void *),
			      void *context, EFI_GUID *group, EFI_EVENT *event)
{
	assert(type == EVT_NOTIFY_SIGNAL && tpl == TPL_CALLBACK && group == &gEfiEventBeforeExitBootServicesGuid);
	assert(!config_calls && !output_calls);
	create_calls++;
	if (scenario == 5) return EFI_DEVICE_ERROR;
	saved_callback = callback;
	saved_context = context;
	*event = event_token;
	return EFI_SUCCESS;
}
static EFI_STATUS mock_close(EFI_EVENT event)
{
	assert(event == event_token);
	close_calls++;
	return EFI_SUCCESS;
}
struct boot_services {
	EFI_STATUS (*LocateProtocol)(EFI_GUID *, void *, void **);
	EFI_STATUS (*CreateEventEx)(UINT32, UINT32, void (*)(EFI_EVENT, void *), void *, EFI_GUID *, EFI_EVENT *);
	EFI_STATUS (*CloseEvent)(EFI_EVENT);
};
static struct boot_services services = { mock_locate, mock_create, mock_close };
static struct boot_services *gBS = &services;

/* ACTUAL_HELPERS */

int main(void)
{
	for (scenario = 0; scenario < 9; scenario++) {
		SAMURAI_PANEL_HANDOFF context;
		protocol = (EFI_QCOM_TLMM_PROTOCOL){ .Revision=1, .ConfigGpio=mock_config, .GpioOut=mock_output };
		if (scenario == 2) protocol.Revision = 0;
		if (scenario == 3) protocol.ConfigGpio = NULL;
		if (scenario == 4) protocol.GpioOut = NULL;
		locate_calls = create_calls = close_calls = config_calls = output_calls = debug_calls = 0;
		physical_reset_level = 1;
		saved_callback = NULL;
		gBS = &services;
		EFI_STATUS status = SamuraiArmPanelHandoff(&context);
		assert(locate_calls == 1 && !config_calls && !output_calls && !context.Attempted);
		if (scenario >= 1 && scenario <= 5) {
			assert(EFI_ERROR(status) && !context.Event);
			assert(create_calls == (scenario == 5));
			SamuraiDisarmPanelHandoff(&context);
			assert(!close_calls && physical_reset_level == 1);
			continue;
		}
		assert(status == EFI_SUCCESS && saved_callback && saved_context == &context);
		if (scenario == 8) {
			/* Returning from LoadImage/StartImage before ExitBootServices must not blank the panel. */
			SamuraiDisarmPanelHandoff(&context);
			assert(close_calls == 1 && !context.Event && !config_calls && !output_calls && physical_reset_level == 1);
			continue;
		}
		saved_callback(event_token, saved_context);
		assert(context.Attempted && config_calls == 1 && output_calls == (scenario != 6));
		assert(context.Status == (scenario == 6 || scenario == 7 ? EFI_DEVICE_ERROR : EFI_SUCCESS));
		assert(physical_reset_level == (scenario == 6 || scenario == 7 ? 1 : 0));
		saved_callback(event_token, saved_context);
		assert(config_calls == 1 && output_calls == (scenario != 6));
		SamuraiDisarmPanelHandoff(&context);
		SamuraiDisarmPanelHandoff(&context);
		assert(close_calls == 1 && !context.Event);
	}
	for (int invalid = 0; invalid < 4; invalid++) {
		SAMURAI_PANEL_HANDOFF context = { .Tlmm=&protocol };
		protocol = (EFI_QCOM_TLMM_PROTOCOL){ .Revision=1, .ConfigGpio=mock_config, .GpioOut=mock_output };
		config_calls = output_calls = 0;
		if (invalid == 0) {
			SamuraiPanelBeforeExitBootServices(event_token, NULL);
		} else {
			if (invalid == 1) context.Tlmm = NULL;
			if (invalid == 2) protocol.ConfigGpio = NULL;
			if (invalid == 3) protocol.GpioOut = NULL;
			SamuraiPanelBeforeExitBootServices(event_token, &context);
			assert(context.Status == EFI_UNSUPPORTED && context.Attempted);
		}
		assert(!config_calls && !output_calls);
	}
	SAMURAI_PANEL_HANDOFF gone = { .Event=event_token };
	gBS = NULL;
	close_calls = 0;
	SamuraiDisarmPanelHandoff(&gone);
	assert(!gone.Event && !close_calls);
	assert(sizeof(protocol) == 48 && offsetof(EFI_QCOM_TLMM_PROTOCOL, GpioOut) == 32);
	printf("14 actual firmware-helper scenarios passed\n");
	return 0;
}

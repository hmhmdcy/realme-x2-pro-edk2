/* Explicit saved-frame profile. Only the shared actual C size/validator APIs. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "gauge-protocol.h"

static int nibble(char c)
{
	if (c >= '0' && c <= '9') return c - '0';
	if (c >= 'a' && c <= 'f') return c - 'a' + 10;
	if (c >= 'A' && c <= 'F') return c - 'A' + 10;
	return -1;
}

int main(int argc, char **argv)
{
	unsigned int profile, identity = 0;
	if (argc < 5 || argc > 19 || !(argc & 1) || strcmp(argv[1], "--profile")) return 2;
	if (!strcmp(argv[2], "standard")) profile = SM_MAC_PROFILE_STANDARD;
	else if (!strcmp(argv[2], "observed-2719-0056-3")) profile = SM_MAC_PROFILE_OBSERVED_2719_0056_3;
	else return 2;
	unsigned int count = (argc - 3) / 2;
	unsigned char packets[8][36];
	unsigned int commands[8];
	for (unsigned int i = 0; i < count; i++) {
		char *end;
		unsigned long cmd = strtoul(argv[3 + 2 * i], &end, 16);
		const char *raw = argv[4 + 2 * i];
		if (!*argv[3 + 2 * i] || *end || cmd > 0xffff || strlen(raw) != 72) return 2;
		commands[i] = cmd;
		for (unsigned int j = 0; j < 36; j++) {
			int a = nibble(raw[2 * j]), b = nibble(raw[2 * j + 1]);
			if (a < 0 || b < 0) return 2;
			packets[i][j] = (a << 4) | b;
		}
	}
	printf("[");
	for (unsigned int i = 0; i < count; i++) {
		int size = commands[i] == 1 ? sm_mac_observe_data_size(1) :
			sm_mac_observe_profile_size(commands[i], profile, identity);
		int rc = sm_mac_validate_sized(packets[i], 36, commands[i], size);
		unsigned int value = 0;
		if (!rc && size == 2) value = sm_le16(packets[i] + 2);
		if (!rc && size == 3) value = packets[i][2] |
			(unsigned int)packets[i][3] << 8 | (unsigned int)packets[i][4] << 16;
		if (!rc && size == 4) value = sm_le32(packets[i] + 2);
		if (commands[i] == 1) identity = !rc && value == 0x2719 ? value : 0;
		printf("%s{\"command\":%u,\"payload_bytes\":%d,\"validate_rc\":%d,\"value\":",
		       i ? "," : "", commands[i], size, rc);
		if (rc || (size != 2 && size != 3 && size != 4)) printf("null");
		else printf("%u", value);
		printf("}");
	}
	printf("]\n");
	return 0;
}

/* Saved bytes only: reuse the provider's actual frame validator. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../protection-query-observer-candidate/gauge-protocol.h"

static int nibble(char c)
{
	if (c >= '0' && c <= '9') return c - '0';
	if (c >= 'a' && c <= 'f') return c - 'a' + 10;
	if (c >= 'A' && c <= 'F') return c - 'A' + 10;
	return -1;
}

int main(int argc, char **argv)
{
	if (argc < 3 || argc > 17 || !(argc & 1)) return 2;
	unsigned char packets[8][36];
	unsigned int commands[8];
	unsigned int count = (argc - 1) / 2;
	for (unsigned int i = 0; i < count; i++) {
		char *end;
		unsigned long cmd = strtoul(argv[1 + 2 * i], &end, 16);
		const char *raw = argv[2 + 2 * i];
		if (!*argv[1 + 2 * i] || *end || cmd > 0xffff || strlen(raw) != 72) return 2;
		commands[i] = cmd;
		for (unsigned int j = 0; j < 36; j++) {
			int a = nibble(raw[2 * j]), b = nibble(raw[2 * j + 1]);
			if (a < 0 || b < 0) return 2;
			packets[i][j] = (a << 4) | b;
		}
	}
	printf("[");
	for (unsigned int i = 0; i < count; i++) {
		int size = sm_mac_observe_data_size(commands[i]);
		int rc = sm_mac_validate_sized(packets[i], 36, commands[i], size);
		printf("%s{\"command\":%u,\"payload_bytes\":%d,\"validate_rc\":%d,\"value\":",
		       i ? "," : "", commands[i], size, rc);
		if (rc || (size != 2 && size != 4)) printf("null");
		else printf("%u", size == 2 ? sm_le16(packets[i] + 2) : sm_le32(packets[i] + 2));
		printf("}");
	}
	printf("]\n");
	return 0;
}

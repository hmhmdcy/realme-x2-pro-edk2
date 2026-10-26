/* Saved 0056 bytes only. Keep the installed provider's size4 result alongside
 * the explicit observed-2719 size3 diagnosis; no status-bit interpretation. */
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
	unsigned char packet[36];
	if (argc != 2 || strlen(argv[1]) != 72) return 2;
	for (unsigned int i = 0; i < 36; i++) {
		int a = nibble(argv[1][2 * i]), b = nibble(argv[1][2 * i + 1]);
		if (a < 0 || b < 0) return 2;
		packet[i] = (a << 4) | b;
	}
	int old = sm_mac_validate_sized(packet, 36, 0x0056, 4);
	int observed = sm_mac_validate_sized(packet, 36, 0x0056, 3);
	printf("{\"command\":86,\"physical_bytes\":36,\"length_byte\":%u,"
	       "\"legacy_payload4_validate_rc\":%d,\"observed_2719_payload3_validate_rc\":%d,"
	       "\"raw_value_u24\":", packet[35], old, observed);
	if (observed) printf("null");
	else printf("%u", packet[2] | (unsigned int)packet[3] << 8 |
		    (unsigned int)packet[4] << 16);
	printf(",\"semantic_compatibility_verified\":false,\"TCA_classification_verified\":false}\n");
	return 0;
}

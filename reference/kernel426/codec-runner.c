/* SPDX-License-Identifier: GPL-2.0-only */
int main(void)
{
	struct vfe_175_ds4_config config = {480, {0, 0, 256}}, bad;
	u32 previous[4] = {0x12345678, 0xaaaaaaaa, 0xffffffff, 0x10000};
	u32 output[4], unchanged[4], input[8];

	assert(vfe_175_ds4_encode(NULL, previous, output) == -EINVAL);
	assert(vfe_175_ds4_encode(&config, NULL, output) == -EINVAL);
	assert(vfe_175_ds4_encode(&config, previous, NULL) == -EINVAL);
	for (unsigned i = 0; i < 7; i++) {
		bad = config;
		switch (i) {
		case 0: bad.input_height = 0; break;
		case 1: bad.input_height = 8194; break;
		case 2: bad.input_height = 479; break;
		case 3: bad.coefficient[0] = 257; break;
		case 4: bad.coefficient[1] = 257; break;
		case 5: bad.coefficient[2] = 255; break;
		case 6: bad.coefficient[0] = bad.coefficient[1] = 256; break;
		}
		memset(output, 0xa7, sizeof(output));
		memcpy(unchanged, output, sizeof(output));
		assert(vfe_175_ds4_encode(&bad, previous, output) == -EINVAL &&
		       !memcmp(output, unchanged, sizeof(output)));
	}
	while (fread(input, sizeof(input), 1, stdin) == 1) {
		config.input_height = input[0];
		for (unsigned i = 0; i < 3; i++) config.coefficient[i] = input[i+1];
		assert(!vfe_175_ds4_encode(&config, input+4, output));
		memcpy(unchanged, input+4, sizeof(unchanged));
		assert(!vfe_175_ds4_encode(&config, unchanged, unchanged) &&
		       !memcmp(output, unchanged, sizeof(output)));
		assert(fwrite(output, sizeof(output), 1, stdout) == 1);
	}
	return 0;
}

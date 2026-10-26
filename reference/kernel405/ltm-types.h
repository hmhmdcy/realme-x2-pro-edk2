/* Quantized LTM13 segment fields. Unsigned LUT bases use 12 bits, except
 * reverse-Gamma bases (14). Deltas are signed at the corresponding width.
 * Signed scale/LCE bases and deltas use 12 bits. No CDM words or addresses.
 */
struct camss_a5_ipe_ltm_unsigned {
	u16 base;
	s16 delta;
};

struct camss_a5_ipe_ltm_signed {
	s16 base, delta;
};

struct camss_a5_ipe_ltm_iq {
	u32 reverse_gamma, local_adaptation, mask_filter;
	u32 bin_init_count;
	u32 rgb2y[4];
	u32 lce_threshold, y_ratio_max;
	u32 mask_kernel[6];
	u32 mask_shift, mask_scale;
	u32 horizontal_termination, vertical_termination;
	u32 data_collection, image_processing;
};

struct camss_a5_ipe_ltm {
	struct camss_a5_ipe_ltm_iq iq;
	u16 weight[12];
	struct camss_a5_ipe_ltm_unsigned la[2][64];
	struct camss_a5_ipe_ltm_unsigned curve[64];
	struct camss_a5_ipe_ltm_signed scale[64];
	struct camss_a5_ipe_ltm_unsigned mask[64];
	struct camss_a5_ipe_ltm_signed lce[2][16];
	struct camss_a5_ipe_ltm_unsigned reverse_gamma[5][64];
};

#define CAMSS_A5_IPE_PROGRAM_LTM 11U
#define CAMSS_A5_IPE_LTM_PRE_OFFSET 32U
#define CAMSS_A5_IPE_LTM_POST_OFFSET 96U
#define CAMSS_A5_IPE_LTM_CST_OFFSET 2784U
#define CAMSS_A5_IPE_LTM_CC_OFFSET 2840U
#define CAMSS_A5_IPE_LTM_CV_OFFSET 2884U
#define CAMSS_A5_IPE_LTM_GAMMA_DMI_OFFSET 2928U
#define CAMSS_A5_IPE_LTM_GAMMA_LUT_OFFSET 2976U
#define CAMSS_A5_IPE_LTM_DMI_OFFSET 6048U
#define CAMSS_A5_IPE_LTM_LUT_OFFSET 6208U
#define CAMSS_A5_IPE_LTM_IQ_BYTES 8944U

int camss_a5_ipe_ltm_check(const struct camss_a5_ipe_ltm *ltm);
int camss_a5_ipe_encode_ltm_iq(void *destination, u32 bytes, u32 iq_iova,
			     const struct camss_a5_ipe_colour *colour,
			     const struct camss_a5_ipe_gamma *gamma,
			     const struct camss_a5_ipe_ltm *ltm);

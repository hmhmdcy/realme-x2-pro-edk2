
int camss_a5_ipe_frame_params_check(const struct qcom_ipe_a5_frame_params *params)
{
	int ret;

	static_assert(sizeof(*params) == 6008);
	static_assert(sizeof(params->colour) == sizeof(struct camss_a5_ipe_colour));
	static_assert(offsetof(struct qcom_ipe_a5_colour, cc) ==
		      offsetof(struct camss_a5_ipe_colour, cc));
	static_assert(offsetof(struct qcom_ipe_a5_colour, cv) ==
		      offsetof(struct camss_a5_ipe_colour, cv));
	static_assert(sizeof(params->gamma) == sizeof(struct camss_a5_ipe_gamma));
	static_assert(sizeof(params->ltm) == sizeof(struct camss_a5_ipe_ltm));
	if (!params)
		return -EINVAL;
	if (!params->version)
		return memchr_inv(params, 0, sizeof(*params)) ? -EINVAL : 0;
	if (params->version != QCOM_IPE_A5_PARAMS_VERSION ||
	    params->size != sizeof(*params) ||
	    params->flags & ~(QCOM_IPE_A5_GAMMA | QCOM_IPE_A5_LTM) ||
	    params->colour.padding ||
	    memchr_inv(params->reserved, 0, sizeof(params->reserved)))
		return -EINVAL;
	ret = camss_a5_ipe_colour_check((const void *)&params->colour);
	if (!ret)
		ret = camss_a5_ipe_gamma_check((const void *)&params->gamma);
	if (!ret)
		ret = camss_a5_ipe_ltm_check((const void *)&params->ltm);
	return ret;
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_frame_params_check);

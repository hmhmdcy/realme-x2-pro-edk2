int IPACamss::prepareIpeParameters(uint64_t epoch, uint32_t sof, uint64_t token,
				 std::vector<uint8_t> *parameters, uint64_t *revision, bool *fresh)
{
	if (!parameters || !revision || !fresh) return -EINVAL;
	parameters->clear(); *revision = 0; *fresh = false;
	if (!running_ || epoch != epoch_) return -ESTALE;
	if (!ipeTone_) return 0;
	const auto *frame = token ? ipeHistory_.pending(token) : nullptr;
	if (token && (!frame || frame->sof != sof || frame->epoch != epoch)) return -ESTALE;
	if (!frame || !frame->luxValid || numericHistory_.busy()) {
		if (committedTone_) {
			const auto *p = reinterpret_cast<const uint8_t *>(&*committedTone_);
			parameters->assign(p, p + sizeof(*committedTone_)); *revision = numericHistory_.revision();
		}
		LOG(IPACamss, Info) << "IPE_TONE_HOLD epoch=" << epoch << " sof=" << sof << " token=" << token
			<< " revision=" << *revision << " bytes=" << parameters->size() << " busy=" << numericHistory_.busy() << " lux-valid=" << bool(frame && frame->luxValid);
		return 0;
	}
	qcom_ipe_a5_frame_params packet; IpeToneState next;
	int ret = ipeTone_->calculate(*frame, numericHistory_.state(), &packet, &next);
	if (ret) {
		LOG(IPACamss, Error) << "IPE_TONE_REJECT sof=" << sof << " token=" << token << " status=" << ret;
		return ret;
	}
	const uint64_t base = numericHistory_.revision();
	ret = numericHistory_.prepare(epoch, sof, token, base, next);
	if (ret) return ret;
	pendingTone_ = packet;
	const auto *p = reinterpret_cast<const uint8_t *>(&packet);
	parameters->assign(p, p + sizeof packet); *revision = base + 1; *fresh = true;
	uint64_t trace = 14695981039346656037ULL;
	for (uint8_t byte : *parameters) { trace ^= byte; trace *= 1099511628211ULL; }
	LOG(IPACamss, Info) << "IPE_TONE_PREPARE epoch=" << epoch << " sof=" << sof << " token=" << token
		<< " base=" << base << " revision=" << *revision << " bytes=" << parameters->size() << " trace=" << trace
		<< " histogram=" << histogramTrace(*frame) << " lux=" << frame->luxIndex << " gain=" << frame->analogueGain
		<< " exposure-index=" << frame->exposureIndex << " previous-ltm-lux=" << numericHistory_.state().ltmLuxIndex << " factory=" << ipeTone_->factoryMode();
	return 0;
}

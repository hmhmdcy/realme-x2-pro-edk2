void IPACamss::frameProcessed(uint64_t epoch, uint32_t sof, uint64_t token, bool success)
{
	if (!running_ || epoch != epoch_) return;
	const auto *frame = ipeHistory_.pending(token);
	const uint64_t trace = frame ? histogramTrace(*frame) : 0;
	const int result = ipeHistory_.resolve(epoch, sof, token, success);
	LOG(IPACamss, Info) << "IPE_RECEIPT epoch=" << epoch << " sof=" << sof << " token=" << token
		<< " success=" << success << " result=" << result << " trace=" << trace
		<< " pending=" << ipeHistory_.pendingCount();
}


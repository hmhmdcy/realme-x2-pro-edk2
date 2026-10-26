# Image501 CDP profile: narrow independent addendum

No blocker found in this delta. The frozen postboot source is `be1b56a1fe38fd46cd8c58e303a8d98c38b6fd154b8db0a32231095b97418eea`. Compared with the executed prior `c490` body, only `check_gauge` changed. SDP still requires source budget and hardware input exactly 500000 µA. CDP requires a 1500000 µA source budget and hardware input within the existing 50–900 mA range in 50 mA steps. Both retain descriptor500, native500, exact opt-in, separate NOW/AVG, and the unchanged charging/protection/CC/CV/temperature checks.

The retained actual postboot04 transport exited 0 and its report passed all nine checks. Independent decoding confirms the wire stdout equals the retained JSON, the embedded payload equals the retained executed payload, and its device body equals the frozen `be1b` source. Its actual classification is CDP1.5A / native500mA / hardware900mA, CC250mA, pack CV8.725V. Both telemetry samples show a valid fault-free Full hold with cause3 and desired_enable0. Standard Battery is Discharging, NOW−70mA and AVG−1mA; this is not reported as Charging and does not require releasing Full.

The old postboot03 failed original is retained. The adoption implementation remains `e689` byte for byte; only its delegated device source pin changes. The collector launcher changes only the validated report key to `startup500_descriptor_and_native500_preserved`; readiness, sampling, settle interval, PID checks and fetch behavior remain unchanged. Existing ten-case and profile receipts are bound to the actual current bytes; no old suite was rerun.

This addendum does not accept physical timing, pixels or a new adoption transaction. In particular, the older physical capture used SDP/hardware500 while this postboot uses CDP/hardware900. A future timing comparison must preserve that difference and cannot attribute every improvement solely to instantaneous-current support.

`review.py` only parses retained local sources and artifacts, checks hashes and writes this leaf's `review.json`. No runtime entry, device, SSH, USB, SDK, build or Git operation is invoked. The prior reviews and receipts remain historical originals.

# Physical validation remains unverified

No physical capture or attached bench instrument was supplied for this audit. Synthetic fixtures must never be relabeled as physical evidence.

For each real ESP32/TMP102 investigation, retain the exact firmware revision, board/sensor variant, wiring/netlist, datasheet revision, capture instrument, channel mapping, voltage threshold, sample rate, timestamps and raw files. Record address-strap state and independently measured supply voltage. Limit experiments to an isolated low-voltage bench with appropriately rated probes.

Collect a working baseline, an intentionally incorrect address, reversed GPIO configuration, and a safely introduced timing/configuration failure. Change one variable at a time; retain both failing and corrected captures. A second engineer should label the cause before reviewing BenchTrace's ranking. Include captures with insufficient sampling and ambiguous boundaries to evaluate abstention.

Report expected fault inclusion, top-ranked cause, unsupported claims, false positives on working baselines, citation validity and relevance of proposed tests. Keep simulated and physical results separate. Do not report general diagnostic accuracy from the existing eleven synthetic scenarios.

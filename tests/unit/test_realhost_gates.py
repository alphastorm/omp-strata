import unittest

from scripts import realhost_gates as gates

# Stock OMP's default compaction threshold for each profile window (the window OMP is given is 1,024 smaller).
THRESHOLDS = {131_072: 110_541, 262_144: 221_952, 524_288: 444_775}


def window(profile_window: int) -> int:
    return gates.omp_window({"omp": {"context_window": profile_window}})


class ContextScaledFixtures(unittest.TestCase):
    """g17's near-limit prompt and g18l's long session follow the profile's window: a fixed 131K-sized g18l session
    peaked at 162K tokens on a 262K profile and never reached OMP's threshold, so the gate could not pass."""

    def test_threshold_follows_stock_omp(self):
        for profile_window, threshold in THRESHOLDS.items():
            self.assertEqual(gates.omp_compaction_threshold(window(profile_window)), threshold)
        self.assertEqual(gates.omp_compaction_threshold(31_744), 31_744 - 16_384)  # the reserve's floor

    def test_g18l_session_passes_the_threshold(self):
        for profile_window, threshold in THRESHOLDS.items():
            docs = gates.g18l_doc_count(window(profile_window))
            self.assertGreater(docs * gates.G18L_DOC_TOKENS, threshold, profile_window)
        self.assertEqual(gates.g18l_doc_count(window(131_072)), 20)  # the 131K profiles' session is unchanged

    def test_g17_near_limit_prompt_stays_just_under_the_threshold(self):
        for profile_window, threshold in THRESHOLDS.items():
            tokens = gates.g17_near_limit_tokens(window(profile_window))
            self.assertLess(tokens, threshold, profile_window)
            self.assertGreater(tokens, 0.9 * threshold, profile_window)


if __name__ == "__main__":
    unittest.main()

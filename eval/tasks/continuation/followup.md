# Phase 2: finish the calibrated scheduler

Resume the calibration task from the previous phase. The instrument is now unavailable. Use its
recorded tool result in this session to repair scheduler.select; the calibration constants and tie
rule are intentionally NOT repeated here. Map each event into the half-open bucket
floor((time - shift) / width), using the recorded shift and width. Keep one event per bucket according
to the recorded tie rule, and return selected event dictionaries in ascending bucket order. Input
sequence numbers are unique integers; event times can be negative; input order is arbitrary. Preserve
all payload fields, do not mutate the input, and do not silently fall back to the old calibration.

Run python -m unittest discover -s tests -v. Change scheduler.py only; visible tests are immutable.
Explain the recovered observation in your final response. This tests transcript continuation, not
restoration of any engine cache. If the observation is missing, report failure rather than guessing.

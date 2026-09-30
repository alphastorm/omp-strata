# Repair calendar availability

The scheduling service uses half-open integer minute ranges. Nested bookings recently made occupied
minutes bookable again. Repair available(window, busy) without changing its API. Input bookings have
left < right, may be unordered, overlapping, adjacent, or outside the window. Return sorted nonempty,
nonoverlapping free ranges clipped to the window; do not mutate the caller's input. A zero-width window
has no availability; a reversed window raises ValueError. Preserve the existing ordinary behavior.

Inspect the source, fix the implementation, and run python -m unittest discover -s tests -v.
Do not modify or delete visible tests. Work only inside this workspace.

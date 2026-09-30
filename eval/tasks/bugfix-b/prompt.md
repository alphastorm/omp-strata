# Repair the log transport decoder

LineDecoder.feed accepts arbitrary chunks of a UTF-8 byte stream. A network packet may end inside a
Unicode code point. Fix fragmented Unicode decoding while preserving incremental delivery: emit only
LF-terminated lines before final=True; remove exactly one CR when it immediately precedes LF; preserve
bare CR and blank lines; emit a nonempty unterminated suffix once at finalization. Invalid UTF-8,
including an incomplete code point on finalization, must raise UnicodeDecodeError. Calls after a
successful finalization raise ValueError. Each instance has independent state.

Run python -m unittest discover -s tests -v. Do not change visible tests or write outside the workspace.

# Settlement contract

CSV is standard UTF-8 CSV with a header and quoting (including quoted commas and embedded newlines).
Columns: account,event,at,kind,amount,reference. Accounts and event ids are opaque text.
at is an offset-aware ISO 8601 timestamp. Amounts are exact signed decimal currency with two decimal
places; they can exceed IEEE-754 integer precision. kind is charge or void; void amounts are ignored.
The first occurrence of (account,event) wins, even when retransmitted later. A void cancels the charge
with (account,reference), irrespective of row order. A reference in another account never cancels it.
Reduce the entire input BEFORE selecting charge timestamps in the half-open [start,end) interval.
Voids outside the reporting interval still cancel charges. Negative charges are refunds and count.
Return account -> integer cents, include a zero sum when surviving charges cancel each other, omit
accounts without surviving selected charges. The CLI prints exactly this object as JSON. Input is
well-formed; no network, database, or third-party package is involved.

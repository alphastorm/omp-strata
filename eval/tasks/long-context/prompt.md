# Implement archived routing decision LC-042

This workspace includes a large synthetic archive of routing decisions, policy revisions and audit
notes. Implement the still-missing behavior approved by rollout ticket LC-042 in routing.bucket.
Retrieve the authoritative ticket, follow its policy-revision reference, and read that policy. Do not
infer its constants or copy another ticket's policy. The policy is not included in this prompt or in
the visible tests. Preserve all pre-cutover and unrelated-route behavior and the held-item behavior.
Timestamps are integer seconds (including negative values); buckets use mathematical floor division.

Inspect selectively with search/read tools; the archive is deliberately much larger than the code.
Run python -m unittest discover -s tests -v. Do not edit docs/ or visible tests; change implementation
only, inside this workspace. Explain which archived revision you used in your final response.

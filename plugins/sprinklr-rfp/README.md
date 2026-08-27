# sprinklr-rfp

Two skills that together answer a customer RFP end to end, with an audit trail.

## `rfp-response`

Point it at a directory of customer files — "answer this RFP", "fill in this
questionnaire", "we got a security questionnaire", "Anforderungskatalog". It handles
arbitrary file structures and languages.

An orchestrator does discovery, scoping and batching, then runs drafting subagents in
parallel over topic batches. Subagents never touch a customer file; each owns one JSON
answer file, which is what makes the parallelism safe. Answers are validated, checked
across batches for contradictions, verified by clean-context agents, and only then
merged back into the customer's own workbook.

Deliverables: answers in the customer's files, plus an internal `STATE.md` audit trail
with confidence, RAG, source links and owners, a companion narrative document where the
format needs one, an evidence-gap register, and a ranked set of vendor questions.

## `atlassian-retrieval`

Read-only retrieval from Sprinklr's Confluence, Jira, JSM, Bitbucket and the rest, via
the `twg` CLI. Useful on its own — "what does our doc say about X", "who owns X",
"catch me up on X" — and it is the grounding backend the RFP skill requires.

It is strictly read-only. It never edits, creates, comments, transitions or deletes.

## The rule that shapes both

Knowledge comes from Atlassian. Neither skill carries product facts about Sprinklr —
what a module does, which SKU carries a capability, whether a channel is supported — and
neither will answer from model recall. Every claim in a bid is retrieved, cited, and
traceable to a page with an owner and a date. Where retrieval finds nothing, the answer
is marked red with a precise question for a human, never filled in with something
plausible.

Read `skills/rfp-response/references/playbook.md` before your first run. Every rule in it
exists because the mistake was made.

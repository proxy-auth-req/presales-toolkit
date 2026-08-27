# Playbook — failure modes and the reasoning behind the rules

Every rule here exists because the mistake was made. Read before starting.

---

## 1. One field cannot serve two audiences

**What happened.** The answer schema had a single `evidence_artifacts` list, briefed
as "state whether we can supply each artefact". That field was then rendered straight
into a customer-facing document. It shipped our internal to-do list ("does not yet
exist as a consolidated document", "would have to be produced for this bid"), names
of internal wiki pages, an internal environment identifier, and refusal commentary
("is not shared externally"). On a scored criterion, that reads as a confession of
disorganisation.

**Rule.** Customer-facing and internal content are separate fields from the first
draft. `evidence_customer` (what we deliver, how) and `evidence_internal`
(availability, owner, what is missing and why). The build script for any
customer-facing document may only read the customer field.

**Why it recurs.** The internal information is genuinely valuable — "someone must
produce a crypto inventory" is exactly what the user needs. The instinct to keep it is
right; the destination is wrong. Route it to an internal register, not to the customer.

---

## 2. Leak detection must be mechanical

Reading for leaks by eye fails. When the regex guard was added and run against the
already-reviewed document, it found 15 instances — including an internal environment
ID sitting in narrative prose, not in the section anyone had flagged.

Guard the *whole* rendered customer text, not the field you suspect. Patterns worth
carrying: internal system and wiki names, environment identifiers, "internal
document/report/guideline", commentary about what we decline to share, our own to-do
phrasing, shouty capitalised negations, and competitor or wrong-provider names.

When a guard fires on something genuinely fine, do not weaken the guard. Record why it
is retained. An honest caveat is worth more than a silent warning list.

---

## 3. Agents cannot see each other — that is the orchestrator's job

Two batches independently produced correct answers that were jointly wrong:

- Two criteria resting on identical evidence carried different confidence tags,
  because one batch had been told to downgrade and the other had not.
- One file stated flatly "no third-party software product is embedded or resold"
  while another batch established that an in-product module is delivered through a
  third-party platform. Both agents were right within their scope. The bid was wrong.

**Rule.** After every wave, actively hunt for contradictions between batches. The
validator cannot infer these; you must read across. When you find one, send the
owning agent back with the specific contradiction, the reasoning, and what must not
change — the agent has the drafting context and will do it better than you.

Also: pass every settled position explicitly into later prompts. A settled position
list in each prompt is cheap; a contradiction in a submitted bid is not.

---

## 4. Cite what you retrieved, not what someone else retrieved

When a batch reuses another's finding, carry the source across. When an agent is told
about a finding it did not retrieve, it must **not** fabricate a source entry — it
records the finding and attributes it to the other batch. One agent did exactly this
unprompted, and it was correct.

---

## 5. Deployment context is decisive and usually undocumented

A hosting provider, region, tenancy model or deployment variant changes many answers.
Internal documentation rarely qualifies facts by these dimensions.

Tag every answer with how well the deployment context is actually evidenced:

| Tag | Meaning |
|---|---|
| `ALL-VARIANTS` | Docs confirm across all deployment variants |
| `<VARIANT>` | Docs explicitly confirm for this one (e.g. `AZURE`, `EU`) |
| `ASSUMED-GENERAL` | Docs describe it with no qualifier — honest default |
| `CONFLICT` | Docs disagree, or status is genuinely unclear. Forces red |

In practice the overwhelming majority land on `ASSUMED-GENERAL`. That is a true and
useful finding about the knowledge base — report it rather than dressing it up.

**Never let an agent claim a specific-variant tag when its own caveat hedges about
that variant.** The validator checks this; it caught a case the orchestrator had
assumed was fine.

Watch for the target environment being *new*. Certifications, audit scopes and
attestations attach to existing environments. Claiming a new one is already in scope
is a factual error that a reviewer will check.

---

## 6. Answer the question the customer actually asked

Questionnaires often presuppose an architecture the product does not have — supported
operating systems, database products, web servers, agents installed on our hosts.

"Not applicable, we are SaaS" reads as evasion and scores zero. Reframe onto what the
architecture provides instead, so the underlying concern (supportability, lifecycle
control, client requirements) is visibly addressed — then answer concretely the parts
that *do* have concrete answers.

Where the requirement is structurally impossible for any vendor of this shape, argue
from architecture rather than policy. "The architecture does not permit it, and here
is the equivalent mechanism" is far stronger than "we do not offer that".

---

## 7. Defensive honesty, precisely scoped

Where the answer is imperfect: lead with what is genuinely provided, scope the gap
precisely rather than vaguely, and name a closure path only if documentation supports
it. Never overclaim, never volunteer weaknesses nobody asked about.

For missing evidence: **substitute first, gap second.** "An evaluation under X does
not exist. As evidence we supply Y." No excuse, no roadmap promise, no internal
reasoning.

Do not volunteer artefacts the customer did not demand. Offering evidence we lack
against a requirement nobody made is a self-inflicted wound — one agent caught this
and deleted two such entries.

A failing mandatory criterion answered honestly is better than a false pass: in formal
procurement a false confirmation is an exclusion and liability risk, not a scoring
question.

---

## 8. Guarded and stale internal content

Internal pages carry external-sharing guardrails, WIP markers, stale dates, draft
status, and known-defect notes. Some are explicitly not for customers.

Check status before quoting. Numbers pulled from a guarded page landed in a
customer-facing workbook and had to be removed. Capacity analyses that frame something
as an internal bottleneck must never reach a bid.

Where two internal sources disagree, do not silently pick the flattering one. Present
both to the user, put no number in customer text, and defer to the contract stage.
The same SLA contradiction was found independently by three batches — that repetition
is itself the signal that it is real.

---

## 9. Promises create obligations

Answers routinely commit to attachments, documents and figures ("an overview will
accompany the offer"). Track every one. Three such promises accumulated here for
artefacts that did not exist. Either someone produces them or the sentence comes out.

---

## 10. Infrastructure will interrupt long runs

Sleep-induced stream stalls killed several agents mid-run. Mitigations, all cheap:

- **Chunked writes** — agents rewrite their whole answer file every 3–5 items.
- **Resume, do not restart** — a resumed agent keeps its retrieval context. Restate
  the brief in the resume message; do not assume transcript recall.
- **Hold a wake lock** for long runs (`caffeinate -i -t <seconds>`).
- **Tell agents what to do when retrieval fails**: draft from what they have and
  record the shortfall as lower confidence plus a precise open question. An
  infrastructure problem must surface as a visible amber, never as invented content.

Single-writer plus one-file-per-agent means a dead agent can never corrupt anything.

---

## 11. Vendor questions are scored, not admin

The bar: if the customer's answer would not change what we write or bid, it is not a
question. Disqualifying: anything answerable from their own document (this actively
signals incompetence), anything answerable from internal docs (that is retrieval
work), padding.

Rank red-turning questions first — a question that can convert a failing mandatory
criterion is worth more than one that improves a score.

Beware ranking artefacts. Ranking on criterion type before severity buried every
question from files that have no criterion-type field. Rank on: can-it-turn-red →
stated impact → current RAG → criterion type.

Declining to ask is often the right call, and agents should be told so explicitly.
Good reasons to decline: the customer's answer is predetermined; the question would
volunteer a weakness they did not ask about; a near-duplicate is already filed.

---

## 12. Report findings, not process

The user needs: which mandatory criteria fail, what evidence is missing, where
internal sources contradict each other, what needs a human before it ships, and what
was promised that nobody has committed to deliver.

Batch counts and RAG tallies are context for those findings, not the headline.

---

## 13. Packaging boundaries decide whether an answer is true

Which product or SKU carries a capability is not trivia — it is the difference between
a bid that survives commercial diligence and one with a hole in it. And it is never
inferable from the capability's name: two things that sound like one product routinely
sit in two, priced separately.

The failure mode is not ignorance, it is **fluency**. An agent that knows the product
family will write a packaging claim without retrieving it, because the claim feels like
general knowledge rather than a fact needing a source. It is a fact needing a source.

**Rule.** Before any answer rests on something being included, retrieve which line item
carries it and cite that source next to the capability claim. Where an answer turns on
integration, retrieve what the platform layer provides *and* what a given commercial
line entitles — they are different questions with different answers. Connector and
module lists get fixed in the SOW, never in a questionnaire cell, so where the retrieved
sources leave the boundary unclear, that is an `open_question` for the deal owner rather
than a guess in a customer file.

---

## 14. Internal docs lag renames — an empty result is not a negative

Internal pages carry the product and channel names that were current when the page was
written, not today's market names. A search on the current name can return a clean empty
result for something that is fully documented under a former one. This has already put a
wrong "not supported" on its way into a customer file: one agent searched the current
name and concluded absence, another searched the older account-type lists and found it
documented in full.

Vendor renames are the common case, but the same applies to anything Sprinklr has
renamed internally, and to any capability the customer names in their own vocabulary
rather than ours.

**Rule.** A negative is a strong claim. Before "not supported" reaches customer-facing
text, retry the earlier name, retry the internal term rather than the customer's, and
try a second entry point. Record in `caveats` which searches were run, so a reviewer can
see the negative was earned. Where a page's last-updated date predates a rename or an
API change, treat it as possibly stale — say so and lower `confidence` rather than
quoting it flat.

---

## 15. Defensive honesty concedes ground it did not need to

§7 tells agents to be defensively honest, and that rule has its own failure mode: an
agent that has talked itself into a limitation will write it down. A clean-context
verification pass over nine finished rows found five false claims — and **three were
false against us**: capability we actually ship, conceded for free, plus one line
declaring a capability separately licensed when it was already inside the bid. The same
pass also caught the opposite error, a mechanism four agents had independently shown was
not GA.

**Rule.** Verify any section that will be scored, before it ships. One verifier per
claim, blocked from `_work/` and from the drafting artefacts — clean context is the
whole point, because an agent that produced an answer will confirm it. Verdict per
assertion: `supported | contradicted | unverifiable | overstated`, with quoted sources,
every one of them retrieved fresh.

Present corrections for sign-off rather than applying them silently, and expect to
re-verify at least one: on the run above, a verifier's own correction was itself wrong
and was withdrawn on a second pass.

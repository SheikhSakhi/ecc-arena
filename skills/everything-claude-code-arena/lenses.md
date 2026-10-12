# The A-to-Z audit

Every judge in this arena scores every blueprint on all sixteen lenses below, 0 to 10 each. This is
the page that catches the gaps a normal review misses: the spend limit nobody wrote down, the voting
rule with no tie-break, the refund path with no owner. A lens scores high only when the blueprint
answers the questions under it with specifics: numbers, names, owners, states. "To be decided later"
scores as a gap.

Weights are in `lenses.json`. The judge writes the per-lens scores; the engine does the arithmetic.

## Scoring anchors, for every lens

- **10**: every question below that applies to this project is answered concretely, and the answers
  hold up when you try to break them.
- **7**: the lens is covered, one or two questions are thin or hand-waved.
- **4**: the lens is mentioned but a question that matters for this project has no real answer.
- **0 to 2**: the lens is absent, or what is written is wrong.
- If a lens genuinely does not apply to the project (no money moves, so lens C is moot), score it 10
  only if the blueprint says so explicitly and correctly. Silence is not "does not apply".

## A. Purpose and scope

- What problem, for whom, and how will anyone know it worked (a metric with a number)?
- What is explicitly out of scope? What is version one versus later?
- What does the user actually asked for say, and is every stated requirement traceable to a part of
  the blueprint?

## B. Legal and compliance

- Which jurisdictions, and which laws bite (consumer protection, privacy such as GDPR or CCPA,
  financial or gambling regulation when money or prizes move, platform and app-store rules, tax)?
- Terms of service, privacy policy, age limits, consent: who writes them, when do users accept them?
- Licenses of every dependency and of the project itself. Trademarks and names.
- Accessibility law where it applies. Data residency. Record-keeping obligations.
- What single legal issue could shut the project down, and what is done about it?

## C. Money, limits and fraud

- Every flow of value: who pays whom, when, how much, in what currency, and who holds it in between.
- Spend limits and caps: per user, per period, per transaction, overall. The numbers, who sets them,
  what happens at the limit, how they are raised or lowered, and how they are enforced technically.
- Quotas and budgets for the project's own costs (API spend, infrastructure, prizes).
- Fees, taxes, refunds, cancellations, chargebacks, disputes: the rule, the window, the owner.
- Reconciliation: how the books are proven right. Fraud: the three most likely scams and the defense.
- Liability when money is lost. What is never allowed.

## D. Governance, rules and disputes

- If users vote, rank, approve or decide anything: who is eligible, one vote per what, weighting,
  quorum, deadlines, changing or withdrawing a vote, ties, what happens to the losing side.
- Sybil and collusion resistance. Secret or public ballots. Audit of results.
- Moderation: what is removed, by whom, how fast, and how a user appeals.
- Disputes between users, between a user and the project: the process and the final authority.
- Who can change the rules, and how users learn that they changed.

## E. Identity, roles and permissions

- How a user proves who they are, how they recover an account, how sessions end.
- Every role and exactly what it can do. How roles are granted and revoked. Admin powers and their
  limits.
- Which actions are logged with who, what and when. Can a user see what was done to their account?
- Multiple accounts, shared accounts, bots, organisations.

## F. Data model and lifecycle

- The entities, their fields, their relationships, and which fields are the source of truth.
- Who owns each piece of data. Retention, deletion on request, export, anonymisation.
- Backups, restore, and how a restore is tested. Migrations of a live system.
- Consistency: what must be transactional, what may be eventually consistent, and where that shows.
- Personal data: where it is, who can read it, how it is minimised.

## G. Core logic and edge cases

- The key objects as state machines: states, allowed transitions, illegal ones, and who may trigger
  each.
- Concurrency: two users doing the same thing at once, the same request twice, out-of-order events.
- Time: time zones, daylight saving, deadlines at midnight, clock skew, retroactive changes.
- Limits: maximum sizes, counts, lengths. Empty states. Zero, negative, enormous, unicode, duplicates.
- The five inputs most likely to break it, and what happens for each.

## H. Security and abuse

- The threat model: who attacks, what they want, what it costs them.
- Authentication and authorisation checks at every boundary. Secrets management. Input validation.
- Rate limiting, bot defense, CAPTCHAs or alternatives, reporting and blocking of abusers.
- Injection, cross-site, SSRF, insecure direct object references, mass assignment where they apply.
- How a breach is detected, contained and disclosed.

## I. Reliability and operations

- The ways it fails (dependency down, bad deploy, data corruption, full disk) and what the user sees.
- Monitoring, the alerts that page a human, and the dashboards someone looks at weekly.
- Deploy, rollback, environments, feature flags. Runbooks for the three most likely incidents.
- Who is on call. What is the acceptable downtime.

## J. Logistics and the real world

- Anything physical or human outside the code: delivery, scheduling, venues, inventory, staff,
  customer support, payouts, prizes, printing, shipping, returns.
- Geography: countries, languages, currencies, holidays, shipping zones.
- Service levels promised to users and how they are met. Capacity of the humans involved.
- The third parties the project depends on in the real world and what happens when one fails.

## K. Integrations and dependencies

- Every external API and vendor: what it is used for, its cost, its limits, its outage behaviour,
  the fallback, and how hard it is to replace.
- Webhooks, retries, idempotency keys, versioning of external contracts.
- What the project exposes to others and how that is versioned and protected.

## L. User experience and communication

- The main flows step by step, including the unhappy paths and the empty first-run state.
- Every notification and email: trigger, content, frequency, opt-out.
- Error messages a user can act on. Onboarding. Mobile, offline, slow network.
- Accessibility (keyboard, screen reader, contrast, target size). Localisation.
- How the user learns the rules that affect them, before those rules apply.

## M. Performance, scale and running cost

- Expected load, the hot paths, and the first thing that breaks at ten times the load.
- Caching, pagination, background work, queues where needed.
- The monthly running cost at launch and at ten times, in numbers.

## N. Testing and quality

- Acceptance criteria per feature. The test plan: unit, integration, end to end, and what each
  covers.
- Fixtures and test data, including for money and permissions. How flaky tests are handled.
- What is checked before every release, and what blocks a release.

## O. Delivery, scope and risk

- Phases and milestones with a rough timeline and the team needed.
- The top risks, each with a mitigation and an owner. Open questions that need the user's answer,
  listed plainly rather than silently decided.
- Cost to build, in a range with the assumptions behind it.

## P. Documentation and handover

- What documentation exists at launch: for users, for operators, for developers.
- Could a competent stranger run and extend this from the blueprint alone? What would they ask first?

## What a gap looks like

- A rule without a number ("reasonable limits apply").
- A flow without an owner ("refunds are handled").
- A state with no way out ("pending review").
- A dependency without a failure plan.
- A requirement from the task that no section answers.
- "Configurable later", "TBD", "as needed", "standard practice".

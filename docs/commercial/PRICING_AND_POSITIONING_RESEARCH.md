# Pricing and Positioning Research (October 2026)

> **Status: hypotheses for the owner's decision.** Nothing in this document is a price list, a recommendation to publish a price, or evidence of demand. No price has been set, announced or deployed.
> Evidence is dated **2026-10-14** (Stage A). The Stage B refresh targeted at 2026-10-24 is `PENDING_FUTURE_REFRESH`: competitor pages and promotions change, and none of the figures below should be quoted without re-reading the live page.
> Evidence ids (`R-nnn`) resolve in `docs/research/research_register.yaml` and are summarised in [RESEARCH_VERIFICATION_2026.md](../research/RESEARCH_VERIFICATION_2026.md).

## 1. What this research can and cannot support

| It can support | It cannot support |
|---|---|
| Where public price points of comparable training products sit, as read from vendor pages on one date | A claim that any price will convert, or that learners will pay it |
| Which pricing *models* exist (subscription, per-course, exam fee, instructor-led) | A recommended price for any course in this repository |
| The channel cost of selling through a marketplace (fee formulas) | Net revenue forecasts (no demand data exists) |
| Which claims the academy is allowed to make about its own material, given the evidence in this repository | Claims about jobs, salaries, certification equivalence or "recognition" |

The courses are **not releasable** today (see [OCT2026_PRODUCTION_READINESS.md](../release/OCT2026_PRODUCTION_READINESS.md)): no course has passed subject-matter review, a learner pilot, an IP/licence decision or owner approval. Pricing work here prepares experiments; it does not authorise a sale.

## 2. Method and limits

- Vendor pages were fetched on 2026-10-14 through a summarising tool and read for prices, billing periods, inclusions and refund terms. Where the page text showed no price (JavaScript-rendered pages) the gap is recorded instead of filling it from third-party sites whose figures conflict.
- Prices are shown in the currency and locale the vendor displayed to this session; promotions were running on some pages and are noted.
- Search-result pages from third parties were used only to discover comparables, never as price evidence.
- Not researched: Udemy and other per-course marketplaces (prices are dynamic and promotional), Real Python (its join page returned HTTP 403; search summaries gave no prices), Hack The Box Academy (HTTP 404 on the pricing URL), TCM Security (HTTP 503), Test Automation University (empty page text).

## 3. Market evidence (as read on 2026-10-14)

| Comparable | Model | Public price points read | Included (per the page) | Evidence | Caveat |
|---|---|---|---|---|---|
| Coursera Plus | Subscription bundle | $59 per month (7-day trial); $399 per year (14-day money-back guarantee) | More than 10,000 courses, Projects, Specializations and Professional Certificates (some excluded; degrees excluded); unlimited certificates | R-080 | A "Save 40%" label has no stated basis or end date; USD for this viewer |
| Google Skills (formerly Cloud Skills Boost) | Free tier plus subscription | Starter: no cost, 35 credits per month; Pro: $29 per month | Pro: unlimited hands-on labs and thousands of courses and labs | R-085 | The old URL redirects to the new domain; currency code not named |
| TryHackMe | Free tier plus subscriptions | Premium shown as EUR 16.99 and EUR 7.35 per month "billed annually"; MAX shown as EUR 29.11 and EUR 17.99 per month "billed annually" | Premium: full beginner paths, a certificate per path, unlimited AttackBox; MAX: advanced paths and persistent AttackBox | R-081 | The page does not label how the two figures per plan relate; a promotion coupon is shown |
| SANS Institute (SEC504) | Instructor-led and OnDemand courses | OnDemand $8,780 USD (4 months of access); live events $8,780-$8,900 USD and other currencies | 44 labs, printed and digital books, audio; GIAC exam attempt is an optional extra | R-082 | A different category (accredited, instructor-led); only 10 of 47 events visible |
| Python Institute (PCAP exam) | Third-party certification exam fee | From $295; with retake from $345; with retake and practice test from $359 | 40 questions, 65 minutes, 70% pass mark | R-083 | An exam fee, not training; this academy issues no third-party certification |
| Pluralsight | Subscription (individual and team plans) | **No prices visible** in the page text | Six individual plans named (Core Tech, AI+, Cloud+, Security+, Data+, Complete) | R-086 | Third-party pages quote conflicting annual figures; none used |
| Gumroad (a sales channel, not a comparable) | Marketplace fees | Direct sales: 10% plus $0.50 per transaction; Discover sales: 30%; no monthly fee | Gumroad handles sales tax obligations since 2025-01-01 | R-084 | Processing and payout fees are not stated on the page |

**What the evidence suggests (hypothesis, not conclusion):** self-paced practical training is publicly sold at the low end as subscriptions between about $29 and $59 per month, with annual bundles in the hundreds of dollars, while an accredited instructor-led security course sits more than two orders of magnitude higher (R-082). A per-course or per-pathway product from a new academy has no price anchor of its own in this evidence; its price would have to be tested.

## 4. Segments and positioning by course

Positioning statements use only properties that this repository can demonstrate. "Not yet" marks a differentiator that exists as design but has no evidence.

| Course | Likely segment | Nearest comparables in the evidence | Demonstrable differentiators today | Not yet demonstrable |
|---|---|---|---|---|
| Python Engineering (partly built; see the premium catalog) | Developers and analysts who need production-quality Python | Subscription libraries (R-080, R-086); exam preparation (R-083) | Every lesson example is executed in tests; labs graded by mutation or hidden exploit tests; results recorded across CPython 3.11-3.15 ([LAB_EXECUTION_EVIDENCE.md](../qa/LAB_EXECUTION_EVIDENCE.md)); each lesson states what was verified and when | Full module coverage; learner outcomes; SME-reviewed items |
| Python Automation | Operations, QA and security staff | R-080, R-086 | Same method; findings-driven analysis of the source | Modules are planned only |
| Java Test Automation | Testers moving to automation | R-080, R-086 | Currency analysis (JUnit 6, Selenium 4.51 changes) | Modules planned only; no executed Java lab yet |
| AI Engineering and AI security | Engineers building and assessing LLM applications | R-080, R-086 | Executed removal facts (LangChain 1.x, OpenAI client), vendor lifecycle awareness, OWASP LLM Top 10 2025 alignment | Modules planned only |
| GCP Data Engineering | Data engineers on Google Cloud | Vendor labs (R-085), R-080 | Verified service renames and retirements | Cloud labs would need a no-cost local-first design; modules planned only |
| Frontend Engineering | New frontend engineers | R-080, R-086 | Verified framework baselines; the personal-data pages found in the source are identified (F-FE-001) and excluded from the planned content | Modules planned only |
| SOC Analyst | Aspiring Tier-1/Tier-2 analysts | Hands-on security labs (R-081), instructor-led (R-082) | One built module (SOC-M04) with executable, measured labs | 13 of 14 modules planned only |
| Cybersecurity tracks | Learners choosing a specialism | R-081, R-082 | Currency analysis (Entra ID, Sentinel, Container Registry) and authorised-lab rules for offensive content | Modules planned only |
| OSINT investigations | Analysts and journalists | R-081 (security labs) | Law and ethics first; synthetic cases | Source licensing conflict unresolved (decision D3); modules planned only |

## 5. Pricing hypotheses to test later

Each hypothesis states the test, the measure and what would falsify it. None has been run.

| ID | Hypothesis | Test design (owner-run, zero or low cost) | Measure | Falsified if |
|---|---|---|---|---|
| H1 | Buyers compare a self-paced module pack with one to two months of a subscription ($29-$59 per month in R-085, R-080) rather than with instructor-led training (R-082) | Interview 10-15 target learners per segment about the alternatives they considered; no price shown | Share naming subscription libraries versus instructor-led as the alternative | A majority name instructor-led or free resources only |
| H2 | A free first module (SOC-M04 or PY-M02) generates qualified interest | Publish one module as a free download behind an optional e-mail field, tracking sign-ups only | Sign-ups per visitor; completion of the lab (self-reported) | Sign-ups at a rate comparable to a generic blog post |
| H3 | A price corridor between one month of a subscription and one annual bundle is plausible for a pathway | Show three corridor positions to separate interview groups as a *hypothetical* offer and record stated intent, not payment | Stated intent by corridor position | No corridor position gets intent above the free option |
| H4 | Team licences (per seat, annual) matter more than individual sales for enterprise-facing content | Ask five organisations about seat-based licences for the SOC pathway | Number asking for a pilot | None asks |
| H5 | Regional pricing improves reach (a vendor in the evidence displays prices in euro, R-081) | Compare interest by region in the interviews | Stated price sensitivity by region | No difference |

Channel cost arithmetic (from R-084, illustrative amounts only - not a price list): a direct sale of an item at $X yields about 0.90 X - 0.50 before payment processing; a Discover sale yields about 0.70 X.

| Illustrative amount X | Direct sale net (before processing) | Discover sale net |
|---|---:|---:|
| $19 | $16.60 | $13.30 |
| $49 | $43.60 | $34.30 |
| $99 | $88.60 | $69.30 |
| $199 | $178.60 | $139.30 |

The fixed fee makes small items proportionally more expensive; a low-priced product has less room for refunds and support.

## 6. Claims policy for any future marketing

| Permitted when true | Prohibited |
|---|---|
| "Every lab result is recorded with the interpreter and tool versions used" (only for built labs, citing the evidence file) | Job, salary, hiring or certification-outcome guarantees |
| "This edition states its content revision date, research verification date, technical baseline and unverified items" | "Industry-recognised", "accredited" or equivalence to any third-party certification (no such recognition exists) |
| "Examples in lessons are executed by automated tests" (built modules only) | "SME-reviewed" or "expert-approved" (no review has happened) |
| "Currency verified on 2026-10-14; refresh planned" | "Latest" or "up to date" without a date and a source |
| Honest module counts (built versus planned) | Describing planned modules as available |

## 7. Risks and unknowns

- **IP and licensing:** the licence holder and terms of the source material are undecided (owner decisions D3 and D4 in [LICENSE-STATUS.md](../../LICENSE-STATUS.md) and [IP_AND_LICENSE_REVIEW.md](../audits/IP_AND_LICENSE_REVIEW.md)); the OSINT source plans to redistribute GPL tools under a proprietary licence. These block any sale of affected content.
- **No demand evidence:** every number above describes competitors, not customers.
- **Stale evidence:** vendor promotions and plan structures change; one page already showed a seasonal promotion banner.
- **Outcome claims:** the academy cannot make learner-outcome claims until a learner pilot has been run.

## 8. Next research actions

1. Stage B (2026-10-24): re-fetch the seven vendor pages and diff the figures; record any change as a new register entry rather than editing these.
2. Obtain prices from vendors whose pages were unreadable (Real Python, Hack The Box Academy, TCM Security, Pluralsight, Test Automation University) using a browser the owner controls.
3. Run H1 and H2 first: they cost nothing and show whether the later hypotheses are worth testing.
4. Resolve decisions D3 and D4 before any listing is created.

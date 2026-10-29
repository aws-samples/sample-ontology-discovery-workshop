---
name: graph-evaluation
description: Use when evaluating the labeled property graph (LPG) schema (T-Box) of a knowledge graph, or comparing schemas that model the same data in different ways, and producing an HTML evaluation report. Also use when the user asks in Korean for a graph or schema evaluation (그래프 평가, 스키마 평가).
---

# Graph Schema (T-Box) Evaluation

Evaluate a labeled property graph (LPG) schema by looking at the T-Box only, and compare schemas that model the same data in different ways. The deliverable is an HTML report for the customer. The report is written in Korean.

Some strings below are quoted in Korean with an English gloss in parentheses. Those are the literal strings to use in the Korean report.

## Workshop integration and completion conditions

- This is the shared execution rule for `/ontoforge-evaluation`. Both Claude and Kiro read this whole file.
  `.claude/commands/ontoforge-evaluation.md` (Claude) and `.kiro/steering/ontoforge-evaluation.md` (Kiro)
  are only entry points that point to this file. Write rules in this file only; do not copy them into the entry files.
- It always runs last: modeling → Gate 1 question verification → Gate 2 data status
  → Gate 3 data location → architecture, export, and deliverable checks → this evaluation.
- Use the current workshop's final `workshop-model.json`. If a comparison is requested, evaluate each explicitly
  named model by the same criteria. Never use a customer case name or an example path as a default input or output.
  Ask the user for a path only when there is no input, or when several candidates exist and the target cannot be decided.
- Even for a single model, perform all of Steps 0 to 4 below, the overall assessment, recommendations, DB considerations,
  limitations, and Appendices A to C. If there is no comparison target, write the comparison parts as a single-model
  analysis. For items without data, record "미확인" (unverified) or "적용 불가" (not applicable) with the reason, and never
  mark a verification as done when it was not performed.
- The evaluation depth is always `comprehensive`. Never present a result of only some steps as the final report.
- Source files are read-only. Perform the T-Box evaluation even when there is no A-Box. If more aggregation is needed,
  give the data owner the read-only queries in Appendix B, and do not connect to a DB without permission or a basis for access.

### Execution and deliverables

1. Confirm the input and context, then follow the whole evaluation flow below.
2. Pass the generic labels and hubs decided in Step 0 with `--generic` and `--hubs`, and run `schema_metrics.py` in this
   skill folder on each input. Label names differ per model.
   Apply the same criteria to compared models. Use full-scale values for the options only if they were actually provided.

   ```bash
   python3 .claude/skills/graph-evaluation/schema_metrics.py "/path/to/workshop-model.json" \
     --generic <generic labels,...> --hubs <hub labels,...>
   ```

3. Review the metric output and every lint item, and record the numbers and the reasons for adopting or excluding each.
   For a metric the script does not print, confirm it with a reproducible extra calculation or mark it "미측정"
   (not measured). If the definition and the code differ, record the difference and use an extra calculation that applies
   the same definition to every model.
4. Actually open and check the public source documents and the current DB documentation, and, following the source rules
   below, separate literature evidence from the criteria set for this evaluation. A list of reference links does not
   replace opening the originals.
5. Write all of the body sections 1 to 7 and Appendices A to C of "Report structure (HTML)" below.
   The final output is `graph-evaluation-report.html` in the same folder as the input file.
   When comparing several models, use the current workshop's artifact folder and state the path.
6. Check every number against the calculation results, and review the disposition of every lint item, whether sources
   were verified, the required sections and appendices, and the SVG figure before delivering the HTML.
   If sharing settings are needed, tell the user, but do not publish externally without a user request.
7. If the model changes after the evaluation, refresh the deliverables and run the evaluation again as the last step.
   The evaluation HTML is a separate final deliverable; never tell the user it is automatically included in an existing ZIP.

### Role of the existing automatic checker

`evaluate.py` and `_quality.py` are auxiliary structure-check tools. They always apply `comprehensive`, but they do not
replace the semantic review, literature research, overall assessment, or customer report writing described below.
If an auxiliary result is needed, pass `--out` with `graph-evaluation-static-check.html` so that it is kept apart from the
final report. When there is no A-Box, do not claim that instance checks were completed.
Its scenario candidates are CANDIDATE only, and a relation name appearing in a string is not a correctness check against the
golden question set.

## Input

- Schema JSON: `tbox.entities` (per label: `label`, `primary_key`, `properties`, `bounded_context`, `status`) and
  `tbox.relations` (per relation: `label`, `src`, `dst`, `cardinality`, and optionally `base_type`, `properties`).
  - A relation key with a `__X__Y` suffix means one relation kind was created per label pair. Count kinds by `base_type`
    (or by the key if there is none).
- Context to confirm together: the purpose of the graph, the graph DB (Kuzu and so on), the scale of the source documents
  (for example the number of contexts), golden question set results, whether it is a sample or the full set, and whether
  real data can be viewed.
- If the data (A-Box) cannot be viewed, infer from label and property names, and state in the report that it is an inference.

## Source rules (must follow)

1. Use only public documents as evidence. Do not cite paid pages, even if part of an abstract is visible in search summaries.
2. Cite a literature source only if you opened the original and confirmed the content is really there. Never cite from a
   search result summary alone.
3. Write a metric introduced by another source as "cited from X" (in the Korean report: "X에서 재인용").
4. Mark a source for which only the abstract was checked with "(초록)" (abstract only).
5. For each evaluation step, state whether the basis is literature or a criterion set for this evaluation. Never describe a
   method that was not actually performed as "referenced" or "followed" (참고, 준용).
   - Example: if OntoClean meta-property tagging was not done, write "적용하지 않음" (not applied). If OQuaRE scoring was
     not done, write "적용하지 않음".
   - The OOPS! pitfall catalogue was not confirmed from public originals, so do not use it as a source.
6. In the report's references (Appendix C), include paper links only. Do not include DB documents, wikis, blogs, or slide decks.
7. The state of DB products (archive status, versions, features) changes over time, so recheck it every time you write a report.

## Number rules (must follow)

1. Before writing the report, run the metrics calculation script below on every schema. Check every number in the report
   against the script output.
2. A metric used to compare models must be calculated with the same definition for every model. Do not drop some items for
   only one model.
   - Example: if "share of relationships without domain information" counts only generic-label-to-generic-label
     (Concept→Concept) for a generic schema, but counts hub-routed ones too for a per-concept-label schema, the generic
     schema looks better than it is (a case where 15 of 15 were correct but 10 was written).
3. Review every lint item the script prints. For an item left out of the report, record the reasoning for leaving it out.
   - Example: a case that wrote only `PART_OF` (N:1) and missed `HAS_IDENTIFIER` (1:N), which is the same kind of problem.
4. Distinguish numbers counted directly (sample) from numbers received (full scale).
5. If the script output differs from the metric definition, use the value calculated directly by the definition as the
   report value, and state that the two values differ and why in the difference paragraph of Section 4.2. Explain the cause
   by naming the relations that were not counted.
   - Example (label names belong to that case): the script counted only generic-to-generic and hub-routed relations and gave
     13/30; counting by the definition (either end is a generic label or a hub) adds the 6 pairs with Concept at one end,
     such as `HAS_IDENTIFIER` and `HAS_STATE`, giving 19/30.

## Evaluation flow

The label, relation, and property names in this document (Concept, Event, Rule, Advertiser, and so on) are examples taken
from a case. Generic labels, hubs, and meta properties differ per model, so do not assume names; read the model and decide
them in Step 0.

### Step 0. Set the premises

- Nature of the graph: judge whether the nodes are terms (concepts) or entities (instances).
  - Signals of a term graph: every node's primary key is `name`, `definition`/`context`/`provenance` properties,
    entity `status: candidate`, a description saying it was extracted from documents.
  - To be sure, count nodes per label (Appendix B query 1). If a label has only 1 node, the label is a name tag, not a class.
- Decide the generic labels and hubs: they differ per model, so read the model, judge, and record the decision.
  - Generic label: a label that holds many kinds of things without a specific domain meaning. The kind is distinguished
    only by a property value such as `kind`.
  - Hub: a label connected horizontally to many domain labels. Like events, rules, or logs, it makes the same relation to
    many targets.
  - `schema_metrics.py` prints candidates (labels without `bounded_context`, and endpoints where the same relation kind
    spreads to 3 or more different labels). Candidates are only hints, and the evaluator decides even when there are none.
  - Apply the same criteria to compared models, and write in report Section 1 (premises) which labels were classified this
    way and why. If a model has no such labels, do not specify any. The "share of relationships without domain information"
    metrics are then not calculated, so mark them "해당 없음" (not applicable) and give the reason.
  - If the meta properties to exclude from domain properties (default `name`, `context`, `definition`, `provenance`, `text`)
    differ from the model's convention, change them with `--meta`.
- Separate sample from full: mark which basis each number uses. A full-scale value that comes from a metadata note or the
  user's description is a number that has not been verified, and say so.
- State that grades (High/Medium/Low, written 상/중/하 in the report) are the evaluator's judgment based on evidence, not
  official thresholds.

### Step 1. Structure checks (this evaluation's own criteria)

These check items are set for this evaluation without literature backing. Severity is High / Medium / Low / Needs
confirmation (in the report: 높음 / 중간 / 낮음 / 확인 필요). Also write the strengths of each model.

- Cardinality constraints on a generic label (for example Concept→Concept). Check N:1, 1:N, and 1:1.
  - N:1 (for example `PART_OF`): every concept can have only one parent. "A budget is part of a campaign" and "a budget is
    part of an ad group" cannot both be stored. Usually severity High.
  - 1:N (for example `HAS_IDENTIFIER`): one target concept can belong to only one source concept. It becomes a problem if
    several concepts share the same identifier. Usually severity Medium.
  - If the constraint is reflected in the actual DDL (Kuzu's `MANY_ONE`, `ONE_MANY`, and so on), valid edges may be rejected
    at load time. Record whether the DDL reflects it and how many edges were rejected in Section 7 (open items).
  - If the same constraint is on a specific label pair (for example Ad→AdGroup N:1), it is natural and counts as a strength.
- Relations whose meanings overlap or that cannot be told apart without a definition (for example `CREATES` "creates and
  manages" versus `MANAGES`).
- A generic relation whose description mixes in a specific domain concept that is not in the schema (for example "manages on
  behalf of advertiser").
- Inconsistent use of enumerations for properties of the same nature (for example `Advertiser.status` is an enum while
  `Campaign.status` is a STRING).
- Mismatch between the primary key and an ID property (for example the primary key is `name` but there is an
  `advertiser_id` property). In a term graph the meaning of the ID property is ambiguous; in an entity graph the primary key
  is wrong.
- Naming inconsistency: a difference between the key and the `label` text (`RemainingBalance` vs `"Remaining Balance"`), the
  same name with different meanings (metadata `status` and property `status`), different names for properties of the same
  nature (`text` vs `definition`), and `base_type` written for only some relations.
- States or identifiers absorbed into properties so that they cannot be linked by edges (for example "a rule that applies to
  the suspended state" cannot be expressed).
- A relation connected to only some of several similar labels (for example `APPLIES_TO` exists for AutoBidding but `ABOUT`
  does not) → Needs confirmation.

### Step 2. Quantitative metrics

Keep literature metrics and metrics made for this evaluation separate. Calculate with the script below.

Literature metrics (record the source and whether it was applied in a table in Appendix A):

| Metric | Definition | Source |
|---|---|---|
| Relationship richness RR | non-inheritance relations ÷ (subclasses + non-inheritance relations) | OntoQA (confirmed in the DISO paper) |
| Attribute richness AR | average number of properties per class | OntoQA |
| Inheritance richness IR | average number of subclasses per class | OntoQA |
| Depth, breadth, multiple inheritance | vertical and horizontal structure of the subClassOf hierarchy, share of nodes with several parents | OntoMetrics |
| Cohesion NoR, NoL, ADIT-LN | number of roots, number of leaves, average root-to-leaf path depth | Yao et al. (2005), cited from Savić's slides |
| Coupling NEC, REC, RI | number of external classes used, number of external class references, number of referenced ontologies | Orme et al. (2006), cited from Savić's slides |

Application rules:

- If there are no is-a (sub/super) relations between concepts, IR is fixed at 0 and RR at 1, and depth, breadth, and multiple
  inheritance cannot be calculated. In that case exclude them and give the reason.
- The usual cause of a missing hierarchy is "no is-a relation was defined in the schema". For a model whose concepts are
  nodes, one `IS_A` relation table can build the hierarchy. DB constraints (one label per node, no table inheritance) add to
  the cause only in a model where a concept is a table. Do not blame the DB alone.
- Use AR in a modified form: the number of domain properties excluding meta properties (name, context, definition,
  provenance, text).
- If cohesion and coupling cannot be used as they are, borrow only the idea as a substitute metric and say so.

Metrics made for this evaluation (state in the appendix that they do not come from literature):

- Share of relationships without domain information: the share of node pairs where at least one end is a generic label or a
  hub decided in Step 0. Calculate with the same definition for every model, and in the table also give the breakdown of
  hub-routed / generic-to-generic / generic at one end (example: "15 / 15, generic-to-generic 10, hub-routed 5").
- Hub dependency: the share of node pairs that have a hub decided in Step 0 at one end.
- Number of direct relations between domain labels, number of domain labels with no direct relation, number of labels with no
  domain property.
- Direct connections between contexts: the number of node pairs between labels with different `bounded_context`.
- Schema growth rate: total labels ÷ contexts, total node pairs ÷ contexts.
- Constraint power: allowed node pairs ÷ possible node pairs.
- Over-constraint: the number of edges that could not be loaded because of undeclared pairs or cardinality constraints
  (measured from the load log).
- Count relation kinds and node pairs separately. Counting only pairs inflates relation diversity.

### Step 3. Semantic review (this evaluation's own criteria)

- Meaning of labels: if a label has only 1 node, the schema is really a term list. Then the schema metrics measure the data,
  not the design.
- Whether to make states and identifiers nodes or properties: if rules or events refer to states in the domain, nodes are
  the better fit.
- Whether an intermediate classification is missing between a category (`kind` and so on) and individual concepts.
- Whether is-a was confused with other relations: do not use part-of (PART_OF), state ("suspended" is not a kind of
  advertiser), or role ("advertiser" is closer to a role) as is-a. Do not describe this viewpoint as applying OntoClean.

### Step 4. Golden question set linkage (this evaluation's own criteria)

The T-Box alone cannot decide which model answers questions better. Propose splitting failed questions by cause.

| Failure cause | Related evaluation item |
|---|---|
| A question the schema cannot express | constraint power, how well the domain is expressed |
| Wrong label or relation chosen at query generation | schema size (number of labels and node pairs) |
| Missing edges at extraction or load | over-constraint, undeclared pairs, cardinality constraints |
| DB syntax or semantic differences (Cypher dialect) | unrelated to the model, count separately |

For each model, write down in advance which cause is likely to be most common, and verify the evaluation with the results.

## Overall assessment table

Include only criteria about the quality of the model itself. DB fit, operations, and query generation burden do not go into
the table; handle them in Section 4.2 (schema size) or Section 6 (DB considerations).

| Criterion (row label in the Korean report) | What it looks at |
|---|---|
| Schema constraint power (스키마 제약력) | How well it blocks wrong connections (also show the over-constraint risk) |
| How much of the domain shows in the schema (스키마에서 도메인이 드러나는 정도) | Whether types are in the schema or only in data values |
| Internal consistency (내부 일관성) | The inconsistencies from Step 1 |
| Scalability (확장성) | How much the schema grows as documents increase |
| Clarity of relation meaning (관계의 의미 명확성) | Whether meaning can be told from the relation name alone |

Show 3 dots = High (상), 2 dots = Medium (중), 1 dot = Low (하), and write the numbers in the rationale column.

## Recommendations

Narrow recommendations to 3 or 4 structural changes and write them in priority order. Individual fixes such as cleaning up
relation names go into the Section 4.1 findings. The following are commonly used recommendations and when they apply.

- Node tables per kind (a third model): create a node table for each `kind` value of the generic schema (for example Entity,
  Identifier, System, Actor, State, Process + Event, Rule). Concepts go in as rows (nodes) of each table, and the primary key
  is the concept name. Declaring relation pairs at the kind level gives constraint power while keeping the schema size fixed.
  Include a DDL example.
- Sub/super (is-a) relations between concepts: add an `IS_A` relation table as N:M. Recommend it only conditionally: (1) the
  golden question set has questions asked by a higher-level concept or needing rule inheritance, and (2) the documents have
  evidence sentences such as "a kind of ~" or "~ includes A and B". Keep it shallow, 2 to 3 levels, do not use part-of, state,
  or role as is-a, and change the extraction criteria together. Adding it makes the hierarchy metrics calculable.
- Classify golden set failures by cause: as in the Step 4 table. Count DB dialect failures separately.
- Decide the graph DB direction: mention Ladybug, Neo4j, and Neptune, based on the DB considerations below. Compare models
  within the same DB, and compare DBs separately with the same model.

## Graph database considerations (as of 2026-10, recheck every time)

Kuzu:
- Repository archived in 2025-10, with 0.11.3 as the last official release. The official extension server was discontinued.
  Community forks: Ladybug (0.17.1 in 2026-06), RyuGraph, and others.
- One label per node and per relation (table name = label). No table inheritance.
- Schema is defined up front. A relation table declares the allowed FROM/TO pairs in advance, and how to add a pair to an
  existing relation table later is unclear in the documentation. Cardinality such as `MANY_ONE` and `ONE_MANY` can be set on a
  relation table.
- No user-defined indexes or constraints (only the primary key index is automatic).
- Embedded DB: only one READ_WRITE Database object per DB path.
- Cypher dialect: pattern matching has walk semantics (edges may repeat), the default variable-length bound is 30, `FOREACH`
  and `CALL { }` subqueries are not supported, use `label(n)` instead of `labels(n)`, and `CALL show_tables()` instead of
  `SHOW`.

Alternatives:

| | Ladybug | Neo4j | Neptune |
|---|---|---|---|
| Maintenance | Active | Active | Managed |
| Labels per node | 1 | Several | Several |
| Schema | Defined up front | Optional (some constraints Enterprise, graph type) | None |
| Constraint power | Same as Kuzu | Applied selectively where needed | Practically none |
| Writes | Single process | Server | Managed cluster |
| LLM query generation | Kuzu dialect | Most familiar dialect | Partial openCypher support |
| Data location | Local | Local if self-hosted | AWS |

- Multiple labels let a node be classified at several levels at once (concept / kind / individual concept). But there is no
  sub/super meaning between labels, so the hierarchy still has to be modeled directly.

## Report structure (HTML)

Do not include a summary section or a metadata block (date, evaluation target, and so on) under the heading. Put the body
directly after the title and a one-sentence introduction. The section titles in the Korean report are given in parentheses.

1. Evaluation target and premises (평가 대상과 전제): model card (node tables / relation kinds / node pairs), list of premises,
   evaluation method table (step / content / literature basis; if there is no literature, "없음 (본 평가 기준)", meaning
   none, this evaluation's own criteria).
2. Overall assessment table (종합 평가표).
3. Structure comparison (구조 비교): a schema figure per model (inline SVG, distinguishing hub-routed relations from direct
   domain relations, grouped by context).
4. Detailed evaluation (상세 평가): 4.1 structure checks (per-model findings table + strengths), 4.2 quantitative metrics (for
   comparison metrics give the breakdown and state the definition in a paragraph; if you changed a value because the
   calculation tool's output differed from the definition, add a paragraph titled '자동 계산 도구의 출력과 정의의 차이',
   meaning the difference between the automatic calculation tool's output and the definition), 4.3 semantic review,
   4.4 golden question set linkage.
5. Recommendations (개선 권고).
6. Graph DB considerations (그래프 DB 고려사항).
7. Open items and limits of the evaluation (확인 필요 사항과 평가의 한계): items that could change the conclusion first, whether
   the cardinality constraints are reflected in the DDL and the number of rejected edges, and what cannot be judged without
   data (accuracy of definitions, whether relations are actually used, whether cardinality matches the real data).
- Appendix A, metric definitions (부록 A): literature metrics table (metric / definition / source / applied in this evaluation)
  + table of metrics made for this evaluation.
- Appendix B, aggregate queries for the data owner (부록 B).
- Appendix C, references: papers only (부록 C).

Because this is a page sent to the customer, tell the user that sharing settings are needed, and also deliver the same
content as an HTML file.

## Report style (HTML)

A calm technical report tone. Keep decoration to a minimum and separate information with color and badges. Do not use
shadows, gradients, or emoji. Do not start with big number tiles or summary cards.

Layout:
- On wide screens (1080px and up), two columns: a 220px table of contents on the left (fixed while scrolling) + the body on the
  right (max 780px). On narrow screens, one column with the table of contents on top.
- 56px between sections, and body paragraph width at most 68 characters.
- Table of contents numbers and section heading numbers use a monospace font in the accent color.

Fonts (Google Fonts, with fallback fonts specified):
- Headings: Noto Serif KR (a Myeongjo serif). h1 is 28 to 40px, section headings 25px.
- Body: IBM Plex Sans KR, 16px, line height 1.75, `word-break: keep-all`.
- Numbers, code, figure labels: IBM Plex Mono. Numeric table cells use `tabular-nums`.
- Above the header title, put a small uppercase kicker (eyebrow) in the accent color.

Color tokens (use every color as a token, and define both light and dark):

| Token | Use | Light | Dark |
|---|---|---|---|
| `--bg` | page background (teal-tinted gray) | #f4f7f7 | #0e1517 |
| `--surface` | card and table background | #ffffff | #152022 |
| `--ink` / `--muted` | body / secondary text | #142124 / #55666b | #e2ecec / #9aacb0 |
| `--line` | borders | #d4dfe0 | #29373a |
| `--accent` / `--accent-soft` | accent, model 1 | #0d6a69 / #e0efee | #5fc6c0 / #15302f |
| `--m2` / `--m2-soft` | model 2 | #4a4ea6 / #e7e8f7 | #a3a6f2 / #24264a |
| `--high` / `--high-soft` | severity High | #b02a20 / #fbe8e5 | #f28a80 / #3a1d1a |
| `--mid` / `--mid-soft` | severity Medium | #8f5c00 / #fbf0d9 | #e6b25a / #362a13 |
| `--low` / `--low-soft` | severity Low | #5a6a6f / #e9eeef | #a5b3b7 / #212c2f |
| `--good` / `--good-soft` | strengths | #1b7440 / #e1f2e7 | #73cf92 / #15301f |
| `--code-bg` | code and table header row background | #ecf2f2 | #1a2528 |

If there are three or more compared models, define one more color token that is distinct from model 2.

Components:
- Model badge: pill shape, light background in the model color + dark text.
- Model card: white card (12px corners, 1px border). Three numbers (node tables / relation kinds / node pairs, monospace 24px)
  and a short description.
- Assessment table score: three 8px-diameter dots, lit dots in the model color. The grade word 상/중/하 (High/Medium/Low)
  next to them.
- Severity chip: rectangle with 4px corners. High is red, Medium amber, Low gray, Needs confirmation navy.
- Strengths box: light green background, with the label "강점" (Strengths).
- Table: put it in a bordered box and scroll horizontally inside the box if it overflows. The header row has a light
  background and small text.
- Recommendations: a card-style list, with an accent-colored circular number on the left (numbers are used because the
  priority is a real order) and small tags below (cost, effect).
- Code block: light background, a "복사" (Copy) button at the top right. If the clipboard is blocked, put the text in a
  selected state.

Structure comparison figure (inline SVG):
- Specify colors with CSS tokens so they are visible in dark mode too.
- Hub node: white background + dark border. Domain node: a light pill in the model 2 color. Generic node (Concept and so on):
  a large light pill in the accent color.
- Hub-routed edge: a light, thin line. Direct domain edge: a thick arrow in the model color.
- Context: a dashed box + a name label.
- Put a legend and a caption under the figure. The caption starts with a bold "모델 N." (Model N.).
- The figure's minimum width is 600px, and on narrow screens it scrolls horizontally inside the figure box.

### Customer report wording rules

The customer does not know this skill's internal tools. In the body, tables, and headings of the report, follow the rules below.

- Do not use script, file, or command names (`schema_metrics.py`, `evaluate.py`, `SKILL.md`) or tool terms such as "script"
  and "lint" (스크립트, 린트). Refer to methods by role: '자동 계산 도구' (automatic calculation tool), '정적 구조 점검 도구'
  (static structure check tool), '점검 항목' (check items).
- When you changed a value because the tool output differed from the definition, the sub-heading is '자동 계산 도구의 출력과
  정의의 차이' (the difference between the automatic calculation tool's output and the definition). Keep tool names,
  execution commands, and raw output in the work report to the user (the chat).
- File names of deliverables delivered with the report (for example `graph-evaluation-static-check.html`) may be used. Do not
  write the path of an internal file that is not delivered; explain its content instead.

## Points that are often confusing when explaining

- A node table (label) is the T-Box, and each row inside it is an A-Box node. "250 labels" is a number of tables, not nodes.
- N:1 means "many A can belong to the same B, but one A has only one B". 1:N is the opposite direction. Explain with an
  example (many ads → one ad group).
- More hierarchy is not better. There are many hierarchy metrics because those metrics came from OWL ontologies. Keep only as
  much as the questions need.

## Appendix B aggregate queries (Kuzu syntax)

They return only counts, not values, so the data owner can run them inside the secure environment and send back only the
numbers.

```cypher
// 1. Node count per node table
MATCH (n) RETURN label(n) AS node_table, count(*) AS cnt ORDER BY cnt DESC;
// 2. Edge count per relation table
MATCH ()-[r]->() RETURN label(r) AS rel_table, count(*) AS cnt ORDER BY cnt DESC;
// 3. kind distribution (generic schema. Concept is an example, so replace it with the generic label name decided in Step 0)
MATCH (c:Concept) RETURN c.kind AS kind, count(*) AS cnt ORDER BY cnt DESC;
// 4. Property fill-rate example
MATCH (a:Advertiser) RETURN count(*) AS nodes, count(a.advertiser_id) AS with_id, count(DISTINCT a.status) AS status_values;
// Actual table list
CALL show_tables() RETURN *;
```

## Appendix C reference papers (publicly verified)

- OntoQA evaluation in the DISO ontology paper (RR, AR, IR formulas): https://arxiv.org/pdf/2401.02540
- Class Granularity (limits of schema metrics): https://arxiv.org/pdf/2411.06385
- OQuaRE (abstract): https://research.manchester.ac.uk/en/publications/oquare-a-square-based-approach-for-evaluating-the-quality-of-onto/
- Harmonizing the OQuaRE Quality Framework (abstract): https://www.scitepress.org/PublishedPapers/2022/110772
- Evaluating Ontological Decisions with OntoClean (CACM): https://cacm.acm.org/research/evaluating-ontological-decisions-with-ontoclean

For checking metric definitions (not to be put in the report's references): the OntoMetrics wiki Graph Metrics and Knowledgebase
Metrics pages, and Savić "Coupling and cohesion of modularized ontologies" (2014 slides).

## Metrics calculation script

Run `schema_metrics.py` in this folder on every schema. The code is not copied into this document (to prevent the two copies
from drifting apart). Usage is in the description at the top of the file. Specify the per-model labels decided in Step 0 with
`--generic` for generic labels and `--hubs` for hubs (if they are not specified, the related metrics are not calculated and
only candidates are printed), and pass `--full-labels`, `--full-pairs`, and `--contexts` if the full scale is known. Use the
same options for compared models.

Lint results are a list of candidates. Judge each item against the Step 1 criteria to decide whether it is a real problem,
assign a severity, and without omission either put it in the report or record why it was left out.

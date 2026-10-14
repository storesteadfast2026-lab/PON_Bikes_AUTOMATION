# PON_CURRENT_STATE — Authoritative Project Continuity Reference

**Project:** PON / Pon.Bike container receiving and product reconciliation  
**Last updated:** 14 October 2026, 10:05 Australia/Adelaide (ACDT)  
**Document revision:** v1014.1005  
**Scope:** evidence available to this conversation and discoverable project materials; **not** a live production audit.  
**Evidence legend:** **VERIFIED** = directly inspected file or execution transcript; **INFERRED** = reasoned interpretation; **HYPOTHESIS** = untested possible cause; **UNKNOWN** = missing evidence. A successful historical log verifies the recorded result at its date, not today's state.

## 1. Project identification and last updated date

PON is an operational receiving, scanning and reconciliation application for Pon.Bike bicycles handled in a warehouse context. This document records the most recent **evidenced** application state, its data contracts, historical development and unresolved investigations. No production files, services, data or macros were modified to compile it. Latest live environment state on 14 October 2026: **UNKNOWN**.

## 2. Executive summary and current development status

- **VERIFIED historical installation:** self-contained PBP persisted visual/order hotfix **1009.0901**, installed on **9 October 2026**, with a successful independent read-only verification at **09:13:39**; its operator log still displays internal label `1009.0838` (a packaging/metadata inconsistency). This is the **latest confirmed installed/working functional state in available evidence**, not an assurance that it is still running now. [E1–E3]
- **VERIFIED functional baseline before hotfix:** **1008.1540** identified by exact file SHA-256 checks; its 155 baseline receiving tests passed just before patching. [E1]
- **VERIFIED tests after hotfix:** 16 dedicated tests and 165 receiving tests passed, and HTTP responded on port 8001 following Docker recreation; separate read-only verification repeated 16 and 165 tests successfully. [E1, E2]
- **NOT VERIFIED:** real operational end-to-end re-download from a previously processed container; full physical reconciliation across all containers; production database backup restoration; Node-based UI tests; today's deployed revision. [E1, E2]
- **OPEN:** `#REF!` observed in an Excel macro workbook when processing SKU `D690006050` although product is present as `PON` in `TL_Prods`; exact failing calculated formula / macro step not reproduced from the saved workbook. [E8–E10]
- **OPEN:** BSIU/BSUI identifier transposition and scan-to-manifest/container allocation discrepancy involving BEAU5399380. [E6, E7, E11]

## 3. Business purpose and operational workflow

**VERIFIED from UI screenshot [E11] and tested package [E3]:** receive a container, upload a customer's manifest, upload the first physical scan, confirm/compare expected versus received bikes, check products, supply Translogix-related data, then complete. UI labels: `Receive & Scan` → `Check Products` → `Translogic` → `Complete`; client manifest and first scan each have independent confirmation. Product Check produces visual classification and printed/exported dimensions; New Product Import assists product-data creation; `Replicate` applies to the genuinely new tail only. The exact steps, permissions, Translogix upload schema and business sign-offs need source/runtime verification.

## 4. Confirmed architecture, technologies and dependencies

**VERIFIED in Docker/operator transcripts [E1, E2]:** Windows 11/PowerShell 5.1 host; Python/Django application (`receiving` app); Docker Compose with a web service and `postgres:16-alpine` database; web exposed at localhost port 8001, container port 8000; `python:3.12-slim` Django image build installs `gnumeric`; Django tests create and destroy an isolated `default` test database. Application code files mentioned in validated patch: `receiving/services.py`, `receiving/views.py`, `receiving/tests.py`, `receiving/test_pbp_green_new_block.py`, `receiving/test_pbp_persisted_visual_order.py`. **VERIFIED:** macro-enabled Excel `.xlsm` files include a VBA binary, but the VBA source was not independently decoded. **UNKNOWN:** actual current full repository tree, pinned Python requirements, Django version, full database schema, environment variables, authentication and production topology. Node was absent from the Django container; this does not prove Node is absent elsewhere.

## 5. Known environments, paths and configurations

- **Historical project path (VERIFIED transcript):** `C:\Docker-Projects\PON_Bikes_Automation`.
- **Historical backup root:** `C:\Docker-Projects\PON_Bikes_Automation_Backups`.
- **Specific recorded pre-change backup directory:** `20261009_091132_before_pbp_persisted_visual_order_completion_1009.0838` beneath that root. **Backup created is recorded; integrity-tested restoration NOT VERIFIED.**
- **Observed Compose services:** `pon_bike_automation_09161055-web-1`, `pon_bike_automation_09161055-db-1` (names may change and must be rediscovered).
- **Observed URL:** `http://localhost:8001`; screenshot `http://localhost:8001/containers/20/` pertains to a historical browser session only. [E11]
- **UNKNOWN:** actual current Compose configuration, file mounts, production DSN, volume names, ports, secrets, current root path and admin user. Never hardcode historical observations into a new script without read-only discovery.

## 6. Latest verified working version and recent version history

| Version/package | Evidence | Status |
|---|---|---|
| `1008.1515` | Referenced as a stable predecessor in the 1008.1540 application log [E12] | Historical; present-day status UNKNOWN |
| `1008.1540` | Exact SHA hashes verified against files before 1009.0901; 155/155 tests passed [E1] | **VERIFIED pre-hotfix functional baseline** |
| `1008.1643` | Historical package discoverable in Library [E15] | Candidate/package existence; deployment NOT VERIFIED |
| `1009.0754` | Prior reported failure searching for a literal source block; legacy package available [E15] | NOT accepted as installed |
| `1009.0815` | Structural patch and focused tests present in archived ZIP [E4]; README in successor describes earlier Node-gating failure [E3] | Package available; successful final installation NOT VERIFIED |
| `1009.0838` | Apply failed looking for extracted `1009.0815` in Downloads; independent verify failed because installed-hash state missing [E5] | **FAILED installation**, no modification reported |
| `1009.0901` | Self-contained archive [E3]; successful Apply and independent Verify logs [E1, E2] | **Latest VERIFIED historical installation** |

**Contradiction handled:** `1009.0901` ZIP contains internal `Completion_1009.0901` directory yet its operator output claims `1009.0838`, and its saved backup name has `1009.0838`. Use outer delivered package identity + independent successful logs as historical release identification; verify current hashes to identify today's installation. **Latest proposed version after 1009.0901: UNKNOWN** (no subsequent package or deployment evidence recovered).

## 7. Application components and individual status

| Component | Evidence-based status | Limitations |
|---|---|---|
| Receive & Scan upload/confirmation | **VERIFIED UI exists** [E11] | End-to-end production acceptance UNKNOWN |
| Manifest reader / header mapping | **VERIFIED UI indicates detected mapping workflow** [E11] | Schema and validation implementation NOT VERIFIED |
| First scan | **VERIFIED UI exists**, CSV/XLSX input contract UNKNOWN | Physical source-of-truth reconciliation OPEN |
| Product Check rendering/export | **VERIFIED tests** at 1009.0901 [E1, E2] | Real past-container download NOT VERIFIED |
| New Product Import and colour classification | **VERIFIED tests** at 1009.0901 [E1, E2] | Historical classification availability per old container UNKNOWN |
| Truly New sort and Replicate | **VERIFIED tests** at 1009.0901 [E1, E2] | Operational browser acceptance pending |
| Product dimensions | **VERIFIED tests** Length / Height / Width [E1, E2] | Macro workbook `#REF!` remains OPEN |
| Translogix/Translogic | **VERIFIED UI step exists** [E11] | Integration contract and actual transfer UNKNOWN |
| Completed status / workflow audit | **VERIFIED UI status exists** [E11] | Transition constraints UNKNOWN |
| Spreadsheet VBA | **VERIFIED VBA embedded** [E8, E9] | VBA code and execution NOT VERIFIED |
| Database recovery | Backup creation in log **VERIFIED** [E1] | Restore and integrity NOT VERIFIED |

## 8. Approved technical and functional decisions

**VERIFIED as historical tested design contracts [E1–E3]:** use *persisted original* `PBP_TO_PON` classification over current Product Master status; display PBP→PON first and colour the **whole row yellow** in Product Check and New Product Import; keep Truly New rows in physical/pallet order; limit Replicate to Truly New tail; maintain dimension order Length, Height, Width; keep PBP-to-PON products distinct from Truly New products; preserve 5.0/95 Excel conversion regression. No migrations or production data updates were executed by the hotfix. **Current implementation of each contract is not newly reverified.**

**Project engineering policy [E13]:** evidence-first changes, read-only diagnostics before uncertain alterations, preconditions, isolated testing, rollback, regression, minimal scope, versioned artefacts with Adelaide-local stamps, no destructive database assumptions. Windows operator scripts should be numbered `.bat` with persistent `OUTPUT` logs and PASS/WARN/FAIL signalling; general prescribed sequence is `01_Open_PowerShell_Here.bat`, `02_Apply_Update.bat`, `03_Verify_Update.bat`, `04_Rollback_Update.bat`, followed by backup/recovery as applicable. **Historical exception:** 1009.0901 shipped `01_Apply_Fix`, `02_Verify_Fix`, `03_Rollback_Fix` instead; prior delivery is not a waiver of latest protocol. No post-1009.0901 code change is authorised by this document.

## 9. Excel workbook structures, macros and data contracts

**Directly inspected OOXML structures (VERIFIED) [E6–E10]:**

| Workbook | Sheets / main structure |
|---|---|
| `ContainerScanMacro4 ONEU11908073.xlsm` | `Original`, `Form1`, `Form2`, ` Barcode Converter` (leading space), `TL_Prods`, `Import`, `New Product Import`, `Cust Container Data`, `Check and Dims`, `Receiving Container Data`; VBA binary present |
| `ContainerScanMacro4 FABIAN Cervelo.xlsm` | Same ten visible worksheet names; VBA binary present |
| `ONEU1198073.xlsx` | `Lines` (note filename differs from ONEU11908073 label) |
| `BEAU5399380.xlsx`, `BSIU9783645.xlsx` | `Lines` |
| `BEAU5399380 PON CON40 12-10-26.xlsx`, `ONEU11908073 PON CON40 13-10-26.xlsx` | `Sheet1`, `Sheet2`, `Sheet3` |
| `PON_BEau5399380_Comparacion_1013.0749.xlsx` | `Resumen`, `Solo escaneados`, `Solo esperados`, `Secuencia escaneo`; earlier generated analysis, not official source |

**Named references actually inspected:** both `.xlsm`: `Prods = TL_Prods!$A:$D`; `Prods2 = TL_Prods!$B:$D`; `LOCGET = Form1!$D:$F`. Older Cervelo `Form2Sort = Form2!$A$2:$C$16`, `Original = Original!$A$1:$B$496`, `customer = 'Cust Container Data'!$B$2:$G$26`. ONEU workbook `Form2Sort = Form2!$A$2:$C$23`, `Original = Original!$A$1:$B$501`, and no workbook-level `customer` name. **Both have** `_xlnm._FilterDatabase` names referring to `Form2!#REF!` and `'Receiving Container Data'!#REF!`; these are broken filter defined names, not proof they are responsible for the observed formula error. **Earlier comparative conversation reported** `Form2!P2` uses `Prods` in both; `Q2` differs (older `Prods2`/B2; newer `Prods`/A2). Those formula differences need direct cell-formula reconfirmation before editing. VBA semantics and macro compatibility UNKNOWN. Avoid bulk workbook replacement or copying old names uncritically.

## 10. Product references, SKU mappings and validation rules

**VERIFIED historical worksheet investigation [E8, E9] plus earlier recorded exact row evidence:** `D690006050` appears within `TL_Prods` as `PON`, with matching code values in columns A, B and D; the earlier row index was reported as 8689, which should be rechecked directly for a new diagnosis. Thus treating it as an automatically 'new product' based merely on `#REF!` is unjustified. **UNKNOWN:** Translogix versus PON product catalogue update frequency, uniqueness constraints, data types and exact transformation at every stage. Preserve codes as text (including leading zeros) and do not silently normalise container letter order.

**Rules requiring verification in code:** distinguish previously existing PON, historically PBP→PON and Truly New using authoritative persisted origin, not a mutable current-master lookup; validate customer manifest SKUs and quantities against individual scan records; report unmatched and duplicate SKU counts separately; use explicit workbook-column and sheet contracts; do not conflate `#REF!` formula failures with missing master-data values.

## 11. Container processing and customer data integration

**BEAU/BSIU incident (historical analysis, 12–13 October) [E6, E7, E14]:** earlier scan/manifest comparison reported **102 scanned bikes / 21 distinct SKUs**, against `BEAU5399380.xlsx` **78 expected / 15 SKUs** and **zero overlapping SKUs**. Comparison with `BSIU9783645.xlsx` was reported as **102/102 units and 21/21 SKUs with matching per-SKU quantities**. Examples previously reported: `D690006503` 20, `D690006502` 18, `D690006083` 10, `D690006084` 10, `D690006527` 8. These are **VERIFIED as earlier analysis outputs and archived comparison workbook; independent recount in this document is NOT VERIFIED**. They establish a compelling document/scan alignment, **not** physical ownership or correct container allocation. Await Lisa/customer confirmation of the printed paperwork mix-up and preserve original manifests.

**Container ID contradiction:** screenshot of container/20 and warning text show `BSUI9783645`; customer's filename is `BSIU9783645.xlsx`. This is a literal **I/U letter transposition**; do not rename the workbook to suppress warning or silently rewrite database identifiers. Validate against bill of lading and physical markings. The UI warning states that filename identity is advisory and workbook content will still be validated; it does not prove that content matching actually succeeded. [E11]

**ONEU incident:** attached `ONEU1198073.xlsx` vs `ContainerScanMacro4 ONEU11908073.xlsm` and `ONEU11908073 PON CON40 13-10-26.xlsx` use non-identical textual identifiers. **UNKNOWN** whether a typo, naming convention or genuinely different container. A visible macro Excel `Form2` screenshot showed `D690006050`, `#REF!` in calculated dimensions/volume, but the uploaded saved `.xlsm` was reported to have blank `Form2!A2`, indicating unsaved/runtime-state discrepancy. Preserve both image and uploaded original; retrieve saved-with-error sample before reproducing calculation. [E8–E10]

## 12. Interfaces, import/export processes and external systems

- **VERIFIED:** customer Excel manifest upload and first-scan upload controls, worksheet-based customer and scan inputs, Product Check/New Product Import Excel outputs, Translogic-labelled workflow step and Gnumeric-based Excel compatibility tooling. [E1, E3, E11]
- **VERIFIED tests:** Excel 5.0/95 conversion test passed; yellow row colouring, classification and dimensions covered by targeted tests. [E1, E2]
- **UNKNOWN:** exact upstream customer export generator, source of scan workbook, Translogix API/file schema, import/export business rules, database transaction model, ERP integration, customer contacts/notification automations and macro execution requirements. Do not infer these from filenames or UI alone.

## 13. Operational scripts, including update and diagnostics

**Archived 1009.0901 ZIP (VERIFIED listing [E3]):** `01_Apply_Fix.bat`, `02_Verify_Fix.bat`, `03_Rollback_Fix.bat`, internal PowerShell operators (`Common.ps1`, `Run_Operator.ps1` and respective operation scripts), `apply_patch.py`, one bundled focused regression module, `PACKAGE_MANIFEST_SHA256.txt`, README, `OUTPUT/README.txt`. Installation log states SHA checks, structural AST in-memory preflight, 155 baseline tests, backup, patch, targeted/full regression suites, Docker build/recreation, HTTP check; verifier independently checked installed hashes and tests. **Rollback success after this installation NOT VERIFIED.**

**Earlier failure:** `1009.0838` externally depends on an extracted `1009.0815` despite its packaging; apply stopped on missing path and verify stopped on missing installed hash state. **Superseded by self-contained 1009.0901 packaging**, not proof that all future installation design problems are cured. [E5]

**Other historical scripts:** `Setup-PON-Database_0916.1242.ps1` found in Library [E16], but deployment status and current compatibility UNKNOWN. Current backup/recovery script suite, complete script index and restore drills UNKNOWN. Future operational releases must follow current mandated public `.bat` order and naming protocol, with independent READ-ONLY Verify and persistent per-step logs.

## 14. Executed tests, dates, results, baseline failures and limitations

| Date (Adelaide) | Phase | Recorded result | Limits |
|---|---|---|---|
| 8 Oct 2026 | 1008.1540 apply | 153 baseline tests passed; swapped dimension headers **and** values; safety backup created [E12] | Separate restore NOT VERIFIED |
| 9 Oct 2026 ~08:50 | 1009.0838 Apply | **FAIL**: missing extracted 1009.0815 package; `Nothing changed` [E5] | No functional test of proposed patch |
| 9 Oct 2026 ~08:50 | 1009.0838 Verify | **FAIL**: installed-hash state missing [E5] | Consequence of Apply failure, not proof of app corruption |
| 9 Oct 2026 09:11–09:12 | 1009.0901 Apply | 155/155 prepatch; 16/16 targeted and 165/165 full after patch; Docker web rebuilt; repeated 16 + 165 post-build; HTTP responsive [E1] | Node tests NOT RUN; full real workflow NOT RUN |
| 9 Oct 2026 09:13 | 1009.0901 Verify | installed hashes and regression contracts passed, 16/16 targeted, 165/165 full, HTTP passed [E2] | READ-ONLY; real Excel visual/manual acceptance NOT RUN |
| 13 Oct 2026 | Workbook incident | Saved `.xlsm` structure and names available; visual `#REF!` documented [E8–E10] | Not a reproduced formula/macro defect in saved state |

**Baseline failures:** 1009.0838 missing-package dependency and missing installed-state verification are confirmed failures; 1009.0815 Node-related failure is described by successor README but was not independently re-run here. **No claim:** full system tests, Node GUI regression, physical receiving accuracy, production restore, persisted-old-container colouring or working macro runtime have passed.

## 15. Open issues, root-cause status, impact and priorities

| Priority | Issue | Confirmed symptom | Root-cause classification / next evidence |
|---|---|---|---|
| P1 | `D690006050` `#REF!` in Form2 | Product appears as `PON` in TL_Prods; screen shows formula error | **UNKNOWN root cause**; HYPOTHESIS: broken lookup chain, workbook calculation or VBA interaction. Capture saved failing workbook, exact cell formulas, calculation mode, input sequence and macro trace. Do not blame filter names without reproduction |
| P1 | BEAU5399380 vs BSIU9783645 allocation | 102 scanned units align with BSIU reference in earlier report, not BEAU | **HYPOTHESIS** wrong printed paperwork; verify physical label, customer manifest and scan link; obtain written customer confirmation |
| P1 | `BSUI9783645` vs `BSIU9783645` | Filename mismatch warning and different identifiers | **VERIFIED mismatch; UNKNOWN authoritative ID**; check bill of lading and container plate before correction |
| P2 | Older PBP→PON container re-export | Automated tests pass | **NOT VERIFIED in production**; exercise a historically persisted container and compare screen/download |
| P2 | Release identity confusion `1009.0901`/`1009.0838` | Operator logs show stale embedded label | **VERIFIED packaging metadata defect**; reconcile release identity before next package |
| P2 | Backup restore assurance | Backup directory reported created | **UNKNOWN functional recoverability**; isolated restoration test and hash/DB validation required |
| P2 | Node UI tests | Skipped in Django container | **NOT RUN**; run appropriate UI suite in isolated environment with Node available |
| P3 | ONEU identifier spelling variation | `ONEU1198073` / `ONEU11908073` appear | **UNKNOWN**; compare original customer references |

## 16. Approved but unimplemented work

**No independently recoverable signed-off implementation backlog was located.** Operational next steps explicitly discussed but not proved completed: real historical PBP re-export acceptance; BEAU/BSIU paperwork/customer sign-off; repair of the macro `#REF!` defect **only after root cause identification**; Node/frontend regressions; independently verified restore. These are **proposed verification tasks**, not automatically approved modifications. Design/build of further importer improvements, integration features or new patch versions is **UNKNOWN / requires explicit approval**.

## 17. Security, production protection and regression constraints

No production-data writes as part of diagnostics. Preflight original hashes, project path, Docker Compose identities and database target; fail closed. Create recoverable backup and prove isolated restoration before destructive operations. Never hardcode production users/passwords, container IDs, ports or volume names. Preserve XLSM VBA, formulas, formatting, named references and original customer rows. Keep input identifiers as text; record original filenames separately from canonical business IDs. Avoid auto-reassigning scans or replacing imported records based on apparent match. Changes require before/after comparison, targeted regression plus full relevant suite, rollback and immutable logs; separate historic `PASS` from new execution evidence. **No script, patch, database mutation or workbook edit accompanies this document.** [E13]

## 18. Existing documentation and its current status

- `ENGINEERING_PROTOCOL.md` — **VERIFIED available**, read via project file search; governing mandatory evidence/change/release protocol [E13].
- 1009.0901 ZIP `README.txt`, manifest and `OUTPUT/README.txt` — **VERIFIED inspected/archive listed** [E3]; release-scoped, not complete architecture documentation.
- 1009.0838 and 1009.0815 release READMEs/manifest — **VERIFIED present**, with a failed/superseded installation dependency [E4, E5].
- `PON_CURRENT_STATE.md` preceding this version — **NOT FOUND in accessible current conversation/project file searches**; cannot assert none exists in repository or elsewhere. Initial continuity draft; **no prior-document change log available**.
- Full architecture document, complete app README, operational runbook, environment file, restore SOP, backlog register, repository HEAD and CI configuration — **UNKNOWN / not retrieved**. Neither ChatGPT conversation continuity nor existing release ZIP supplies a complete live source checkout.

## 19. Recommended next steps (priority order)

1. **READ-ONLY runtime inventory:** discover live PON project root, Compose configuration, running image ID, repository state, hashes of deployed `receiving` source, database/table counts and current application port. Compare against 9 Oct saved evidence without mutating data.
2. **Investigate P1 ONEU macro error:** obtain workbook saved after `#REF!` appears, precise failing cell addresses and formulas, calculation-state/Excel version, macro input steps, and compare named ranges/formulas with prior workbook under isolated conditions. Create regression reproducer before fix.
3. **Reconcile BEAU/BSIU:** customer-written confirmation plus physical label and shipping documents; map scan sessions to the actual container/job order and preserve original scan event IDs; no auto-reassignment.
4. **Prove 1009.0901 operational acceptance:** select a historical PBP→PON case with original-classification evidence and inspect new Product Check and New Product Import exports; verify yellow entire rows, ordering, and unaffected Truly New dimensions.
5. **Read-only end-to-end test inventory** for Excel parser, Node/frontend suite, Translogic stage and negative header-mapping cases; run against isolated copied inputs only.
6. **Backup validation:** inspect saved backup manifests and perform fully isolated restore to demonstrate code and data recovery (never production restore as an unapproved test).
7. Consolidate repository docs and pending-work register, and standardise release ID + mandated operator `.bat` interface in the **next approved** change.

## 20. Missing information and required verification

**UNKNOWN:** source repository/current commit, exact current deployed version beyond 9 October logs, database credentials/schema/migrations, Docker configuration, current volume map, package restore effectiveness, actual XLSM macro VBA logic, Excel application recalculation after scan upload, content validation of ONEU live workbook, full customer file schemas/constraints, definitive container numbers and live scan assignment, present app and parser fault traces, entire project chat `Chat.pon.old.3` as an exported transcript, and full official documentation inventory. No claim of access to inaccessible chat messages, current Windows machine, production DB, Macros Editor or external Translogix tenant is made.

## 21. Evidence sources and traceability

| ID | Source and scope | Status |
|---|---|---|
| E1 | `01_Apply_Fix(1).txt`, 9 Oct 2026, applied hotfix, before/after tests, Docker build, backup | **VERIFIED** locally inspected |
| E2 | `02_Verify_Fix(1).txt`, 9 Oct 2026, independent READ-ONLY verification | **VERIFIED** locally inspected |
| E3 | `PON_Hotfix_PBP_Persisted_Visual_Order_SelfContained_1009.0901.zip`, manifest, README, operator scripts, structural patch, test payload | **VERIFIED** ZIP members/README inspected; production execution separately E1/E2 |
| E4 | `PON_Hotfix_PBP_Persisted_Visual_Order_1009.0815.zip` | **VERIFIED** archived package available and contents listed |
| E5 | `01_Apply_Fix.txt`, `02_Verify_Fix.txt`, failed 1009.0838 attempt; `...1009.0838.zip` | **VERIFIED** logs and ZIP inspected |
| E6 | `BEAU5399380 PON CON40 12-10-26.xlsx`, `BEAU5399380.xlsx`, `BSIU9783645.xlsx` | **VERIFIED** source existence and sheet lists; per-SKU totals rely on prior analysis [E14] |
| E7 | `PON_BEau5399380_Comparacion_1013.0749.xlsx` | **VERIFIED** generated comparison workbook present, not source-of-truth manifest |
| E8 | `ContainerScanMacro4 ONEU11908073.xlsm`, `ContainerScanMacro4 FABIAN Cervelo.xlsm` | **VERIFIED** OOXML sheet/defined-name structures and embedded VBA binary presence |
| E9 | `ONEU1198073.xlsx`, `ONEU11908073 PON CON40 13-10-26.xlsx` | **VERIFIED** existence and sheets; numeric content/current mapping not comprehensively audited |
| E10 | Images `image(20261013-035908).png`, `image(20261013-040048).png`; prior discussion about Form2 lookup errors | **VERIFIED** screenshots available; formula root cause UNKNOWN |
| E11 | `image(20261012-212444).png`, container/20 upload UI and filename warning | **VERIFIED** historical screenshot |
| E12 | `01_Apply_Fix(20261008-052227).txt` discovered via project search, 1008.1540 | **VERIFIED** relevant excerpt; full environment not audited |
| E13 | Project `ENGINEERING_PROTOCOL.md` discovered via files search | **VERIFIED** governing protocol excerpts |
| E14 | Earlier PON project discussion and generated 13 Oct comparison report | **Historical report**; not a fresh recount of all SKU quantities |
| E15 | Project Library listing of earlier PON release ZIP names/versions | **VERIFIED** archive metadata only |
| E16 | `Setup-PON-Database_0916.1242.ps1` discovered in project file search | **VERIFIED** existence; current script readiness UNKNOWN |

**Evidence strength:** direct operator logs validate historical execution on named machine; package inspection validates composition but not deployment; worksheet OOXML inspection validates structure/names but not Excel's dynamic evaluation or VBA behaviour; screenshots prove a visible state, not upstream cause; earlier assistant reports are not promoted to fresh independent validation. A project file search identified the engineering protocol but did not provide a complete repo checkout or export of every historical conversation.

## 22. Instructions for continuity in the next ChatGPT conversation

1. Start by reading `docs/PON_CURRENT_STATE.md`, `ENGINEERING_PROTOCOL.md`, actual repository README and current pending-work register if available; compare revision/time and supersede only with new evidence.
2. Treat **1009.0901 as the latest confirmed *historical* installed hotfix**, and **1008.1540 as its verified prepatch base**. Never call either the presently deployed version without a fresh read-only inventory.
3. Use the evidence legend explicitly; cite file names, test dates, file hashes, sample container IDs and exact test outcomes. Keep hypothesised root causes separate from verified symptoms.
4. For workbook problems, inspect original uploaded `.xlsm` and `.xlsx` sheets, header rows, cell formulas, named ranges and VBA before proposing changes. `D690006050` is known historically as PON; `#REF!` is not proof of an unknown product. Do not confuse `BSIU9783645` with `BSUI9783645`, or `ONEU1198073` with `ONEU11908073`.
5. For production tasks, first discover actual environment; conduct READ-ONLY diagnostics and ask for critical missing evidence rather than fabricating paths, settings, filenames, models or test results.
6. Reproduce the defect, add targeted regression, test in isolation, protect customer/production data, compare baseline and candidate tests, prepare rollback and obtain approval before writes.
7. Preserve previously working PBP→PON colour/order, Truly New physical order, Replicate restrictions, Length/Height/Width ordering and workbook/macro data integrity.
8. Follow contemporary mandated `.bat` entry points, log/colour conventions, Adelaide-time artefact naming and documented release gates. Do not package software merely because a diagnostic log is available.
9. Update this document only after evidence reconciliation, retaining traceable provenance and an incremented dated copy; keep stable and dated Markdown copies byte-identical.

## Change log

| Revision | Date (Adelaide) | Change |
|---|---|---|
| v1014.1005 | 14 October 2026 10:05 | Initial continuity reference constructed from accessible project protocol, packages, installation logs, user-supplied workbooks, screenshots and earlier PON discussion. No accessible earlier `PON_CURRENT_STATE.md` to diff. |

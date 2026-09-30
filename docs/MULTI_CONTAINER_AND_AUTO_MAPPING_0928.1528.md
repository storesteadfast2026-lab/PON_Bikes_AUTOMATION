# Multi-container manifest and automatic mapping

## Normal client-manifest path
Upload -> Analyse workbook -> Review detected mapping only when required -> Validate Preview -> Confirm.

When an exact confirmed Customer/workbook structure is recognised, the mapping screen is skipped and the operator goes directly to Validate Preview.

## Multi-container behaviour
A client workbook may contain multiple Container IDs. PON.BIKE normalises each identifier, groups rows by container, and keeps each operational process independent.

The current container receives only its own rows. Additional IDs are either linked to an existing container or created as `PENDING` with no Job Order. The shared source workbook is traceable through each container-specific SourceFile/ImportBatch relationship.

## Job Order gate
A Job Order is unique to one container. Auto-created pending containers may already have a validated Client Manifest and advised quantity, but First Scan is blocked until the operator assigns a unique Job Order.

## Auto-mapping signals
The mapper combines:
- header aliases
- value/data patterns
- Container-ID patterns
- confirmed Customer structure profiles
- Product Master code matches where an active catalogue is available

Confidence policy:
- 95-100: high confidence
- 75-94: suggested / review recommended
- below 75: no forced mapping

## Scanner preparation
The resulting structure supports a future scanner path:
Scan Container -> find existing Pending container -> manifest/advised already known -> request Job Order if missing -> Ready to Receive.
No full scanner subsystem is introduced by this release.

# 04 — Client Manifest Import

Client manifests are uploaded as controlled source files and pass through the existing mapping/preview/confirmation workflow.

## Multi-container manifests

A single workbook may contain rows for more than one container. Container identifiers are normalised for comparison (trimmed, upper-cased, and internal spaces removed where they form a valid container-style identifier).

On confirmation:

- the current container receives only its rows;
- additional detected containers are created as PENDING when they do not exist;
- existing containers are not duplicated;
- each container receives only its own advised subset;
- source provenance is retained.

## Safety

The operator does not manually split the workbook. Quantities, scans, movements and outputs remain scoped to the relevant Container.

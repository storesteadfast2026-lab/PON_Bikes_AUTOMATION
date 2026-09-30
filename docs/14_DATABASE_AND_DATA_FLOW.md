# 14 — Database and Data Flow

The application uses Django with PostgreSQL. Operational records are persisted across incremental releases; update packages must not recreate the database or remove Docker volumes.

High-level data flow:

```text
SourceFile
   ↓ mapping / preview / confirmation
ImportBatch + NormalizedLine
   ↓
Container workflow calculations
   ├─ Product Master comparison / ProductDefinition
   ├─ PRODUCT_MOVES import / reconciliation
   └─ Generated outputs / reports
```

Container, Customer, imports, scans, Job Orders, Product definitions, dictionary/configuration and audit/history data must survive updates.

Presentation-only changes must not create migrations. `makemigrations --check --dry-run` is part of release validation.

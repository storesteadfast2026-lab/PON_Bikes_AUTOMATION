# Validation 0918.0815

Change: sort final `UPStockSerial.csv` rows by ascending numeric Movement.

Validation performed:

- Python `compileall` for `receiving` and `config`: PASS.
- Regression test added to `receiving/tests.py`: out-of-order Movement rows are written in ascending Movement order while keeping their serial_no and Loc associations unchanged.
- Real-file comparison used the two files supplied for the current FDCU0321443 process:
  - application-generated `UPStockSerial.csv`: 85 nonblank bike rows;
  - legacy Excel-generated `UPStockSerial2.csv`: 85 nonblank bike rows.
- After applying the new writer order, all 85 `(Movement, serial_no, Loc)` triples matched the Excel file in the same order: PASS.
- Rebuilt output using the production writer format (`Movement,serial_no,Loc`, Movement right-justified to 10 characters, CRLF line endings, padded to 500 data rows): byte-for-byte identical to the Excel reference: PASS.
- No database schema change: no migration required.

Runtime note: a full Docker/Django integration test is still expected in the user's installed environment after rebuilding the web image, because the sandbox does not share the user's live PostgreSQL/database or Windows mounts.

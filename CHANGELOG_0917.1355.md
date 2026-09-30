# PON Bike Automation — 0917.1355

## Short Name Dictionary in Django Administration

- Added **Administration → Short name dictionary**.
- Shows each XML-learned word/token rule with:
  - Original word (`source`)
  - Abbreviation (`target`)
  - Supporting occurrences
  - Confidence
  - Characters saved
  - Active status
  - Source XML catalogue
- `target` and `active` can be edited directly from the Django Admin list.
- Administrators can also add a manual rule for the active catalogue when a needed abbreviation is not yet learned from the XML.
- Source/statistics remain read-only because they are learned from the XML.
- The ShortName suggestion engine now uses the active/editable Django rules when they exist.
- Exact historical LongName → ShortName matches remain in the XML dictionary and continue to have first priority.
- Migration `0007_short_name_dictionary_rule` populates the Django table from existing `ProductCatalog.name_dictionary` data, so the current ~60 learned rules become visible after migration.

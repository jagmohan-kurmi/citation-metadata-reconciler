# Citation Metadata Reconciler

Parse BibTeX, RIS, and CSL JSON; inspect DOI and required-field structure; rank user-provided metadata candidates; and apply only explicit, confirmed mappings.

## Install and use

```console
python -m pip install .
citation-metadata-reconciler fixtures/sample.bib --candidates fixtures/candidates.json --output report.json
```

Candidate files are JSON arrays with stable `id` values and source metadata. To apply a candidate, provide a mapping JSON object keyed by input record ID, for example `{"ref1":{"candidate_id":"fixture-1","confirm":true}}`, and pass it with `--mapping`. Only missing values are filled; original source records remain in the output. Exit codes are `0` (no validation findings), `1` (validation findings exported), and `2` (invalid/unreadable input or output). No network lookup is performed.

## Limits

The tool organizes researcher-supplied records and does not replace scholarly judgment. Verify outputs against original sources.

## Tests

```console
python -m unittest discover -s tests -v
```

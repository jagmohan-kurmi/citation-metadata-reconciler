# Research basis

Research basis: Crossref documents its REST API and metadata deposited by members (https://www.crossref.org/documentation/retrieve-metadata/rest-api/); OpenAlex documents an open scholarly catalog and API (https://docs.openalex.org/). Neither source is complete or authoritative for every work. DOI Foundation syntax references the DOI Handbook (https://www.doi.org/doi-handbook/). CSL JSON is a widely used citation data format documented by Citation Style Language (https://citeproc-js.readthedocs.io/en/latest/csl-json/). The reconciler accepts only user-provided metadata fixtures; it performs no network lookup. Candidate ranking is heuristic and only a confirmed explicit mapping can populate a chosen record. Original records remain embedded unchanged.

## Limits

The parser supports common BibTeX, RIS, and CSL JSON forms, not every extension or malformed export. DOI checks are syntax checks, not resolution or proof of identity. Candidate ordering is heuristic, sources may be incomplete, and only explicit confirmed mappings can copy missing fields; researchers must verify metadata against authoritative records.

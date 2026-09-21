# Raw data — not committed

The source file is 142 MB, above GitHub's limit.

**Source:** City of Toronto Open Data — Cleared Building Permits since 2017
**Portal:** https://open.toronto.ca/dataset/building-permits-cleared-permits/
**CKAN resource id:** `a96c0ba4-3026-402b-b09d-5b1268b8f810`
**Extracted:** 2026-09-20 (portal metadata_modified 2026-09-20T11:17:04)
**md5:** `d5f431c2522692932fbb6040c39ccf54`
**Rows:** 438,949 · **Columns:** 32

To reproduce: download "Cleared Building Permits since 2017" (CSV) from the
portal, save it here as `cleared_permits_since_2017.csv`, and run
`python python/01_profile.py`.

The file refreshes daily, so a later download will differ. `ai/qa_reviewer.py`
compares against the baselines from this extract and reports what has moved.

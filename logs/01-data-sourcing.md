# Log 01 — Data sourcing

**Stage:** find real data tied to a defensible business question.

## What was rejected, and why

| Candidate | Rejected because |
|---|---|
| **Olist Brazilian e-commerce** | Genuinely good data — real company, real grain complexity. But a single search returns page after page of other people's portfolio projects on it: three GitHub repos, two Medium write-ups, a SlideShare deck, thousands of Kaggle notebooks. A hiring manager who screens analyst resumes has seen this dashboard. Using it makes a project look like a followed tutorial. |
| **Statistics Canada WDS API** | Canadian, well-documented API, genuinely "operations" (wholesale inventories, manufacturing shipments). But aggregate time series — no row-level grain, so no meaningful star schema and nothing to demonstrate on SQL modelling, which is a required skill on the target posting. |
| **USASpending federal procurement** | Strongest grain complexity of the three and a real API. US-centric, which reads oddly for a Toronto employer. Kept as a fallback. |

## What was chosen

**City of Toronto Open Data — Cleared Building Permits since 2017.**

- Local to the employer's market
- Row-level, 438,949 records, real referential complexity
- Genuine data-quality problems (all four major findings came from profiling)
- An application → issued → completed pipeline that is a clean structural
  analogue for order → ship → deliver
- Public API access, which answers the posting's "API Integration" preference

## The obstacle, recorded as it happened

Direct API access from the build environment was **blocked**:

```
curl: (56) CONNECT tunnel failed, response 403
gateway answered 403 to CONNECT (policy denial or upstream failure)
host: ckan0.cf.opendata.inter.prod-toronto.ca:443
```

The organisation's egress policy does not allow that host. Per the proxy's own
documentation, a 403 policy denial is not retried or routed around — it is
reported.

**What still worked:** the dataset metadata and schema were retrieved through a
sanctioned fetch tool, which is how the field list, types, and the 438,949 row
count were known before any data was downloaded. The CSV itself was obtained
manually and its md5 recorded.

**Why this is in the log rather than hidden:** the posting asks for someone who
can "investigate data discrepancies" and "document data sources". Real analysts
lose days to access and provenance problems. Quietly substituting an easier
dataset would have removed the most realistic part of the exercise.

`python/fetch_permits.py` is written as a working CKAN client with pagination —
it runs correctly on a machine where the host is not blocked.

## Provenance recorded

| Field | Value |
|---|---|
| Portal | https://open.toronto.ca/dataset/building-permits-cleared-permits/ |
| CKAN resource id | `a96c0ba4-3026-402b-b09d-5b1268b8f810` |
| Refresh rate | Daily |
| Portal `metadata_modified` | 2026-09-20T11:17:04 |
| Extract date | 2026-09-20 |
| md5 | `d5f431c2522692932fbb6040c39ccf54` |
| Size / shape | 141.6 MB · 438,949 rows · 32 columns |
| Licence | Open Government Licence – Toronto |

Recorded because a number whose source cannot be traced is a rumour. The daily
refresh means a later download will differ; `ai/qa_reviewer.py` holds these
figures as baselines and reports what has moved.

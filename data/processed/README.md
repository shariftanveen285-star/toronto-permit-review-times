# Processed data

Star-schema tables produced by `python/02_clean.py`.

`fact_permits.csv` (438,949 rows) is not committed — regenerate it by running
the cleaning script. The four dimension tables are small and are committed, so
the schema is readable without running anything.

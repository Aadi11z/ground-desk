# GroundDesk Retrieval Benchmark Report

> **Controlled Gemini slice:** This is not a full public benchmark result. It validates the configured API embedding path on a reproducibly sampled labelled subset.

- **Dataset:** nfcorpus_gemini_slice (test split)
- **Corpus documents:** 150
- **Evaluated labelled queries:** 5 / 5
- **Indexed chunks:** 277
- **Embeddings:** `gemini-embedding-2` (`gemini`)
- **Sampling:** 5 labelled queries, 150 documents, seed `42`
- **Index build time:** 453.68s
- **Vector footprint:** 5.68 MiB

## Retrieval Performance

| Strategy | Recall@5 | Success@5 | MRR@10 | nDCG@10 | MAP@10 | No hit@10 | p50 ms | p95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| dense+lexical | 0.569 | 0.800 | 0.800 | 0.663 | 0.606 | 0.200 | 3041.8 | 3125.5 |
| hybrid+lexical | 0.569 | 0.800 | 0.800 | 0.663 | 0.606 | 0.200 | 3045.1 | 3099.3 |
| adaptive+lexical | 0.569 | 0.800 | 0.800 | 0.663 | 0.606 | 0.200 | 4580.8 | 4597.4 |

## Interpretation Boundary

- This report measures retrieval ranking against dataset relevance labels; it does not prove generated answer faithfulness.
- Scores are document-level: retrieved chunks are mapped back to their source document IDs before comparison with qrels.
- Latency is measured on the benchmark runner machine; it is not a hosted-service latency guarantee.
- If a query limit was used, the report is a development run, not a full benchmark result.
- API latency includes a `1.10s` per-request delay intentionally applied to protect free-tier quota.

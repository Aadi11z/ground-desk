# GroundDesk Retrieval Benchmark Report

- **Dataset:** nfcorpus (test split)
- **Corpus documents:** 3,633
- **Evaluated labelled queries:** 323 / 323
- **Indexed chunks:** 6,549
- **Embeddings:** `BAAI/bge-small-en-v1.5` (`sentence-transformers`)
- **Index build time:** 209.88s
- **Vector footprint:** 9.59 MiB

## Retrieval Performance

| Strategy | Recall@5 | Success@5 | MRR@10 | nDCG@10 | MAP@10 | No hit@10 | p50 ms | p95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| dense+lexical | 0.124 | 0.644 | 0.544 | 0.326 | 0.230 | 0.322 | 30.5 | 102.7 |
| hybrid+lexical | 0.129 | 0.641 | 0.550 | 0.318 | 0.226 | 0.307 | 37.1 | 54.4 |
| adaptive+lexical | 0.122 | 0.632 | 0.539 | 0.311 | 0.219 | 0.316 | 51.4 | 67.4 |

## Interpretation Boundary

- This report measures retrieval ranking against dataset relevance labels; it does not prove generated answer faithfulness.
- Scores are document-level: retrieved chunks are mapped back to their source document IDs before comparison with qrels.
- Latency is measured on the benchmark runner machine; it is not a hosted-service latency guarantee.
- If a query limit was used, the report is a development run, not a full benchmark result.

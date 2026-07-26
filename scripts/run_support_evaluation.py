"""Run product-specific GroundDesk evidence and escalation evaluation.

Examples:
    ./venv/bin/python scripts/run_support_evaluation.py

    ./venv/bin/python scripts/run_support_evaluation.py \
      --embedding-provider gemini --embedding-model gemini-embedding-2 \
      --embedding-dimensions 768,1536,3072 --generation-provider gemini \
      --allow-provider-api-calls
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import Settings  # noqa: E402
from app.evals.support_dataset import (  # noqa: E402
    evaluate_support_dataset,
    load_support_dataset,
    report_as_markdown,
)
from app.rag.generation.agent import SupportAgent  # noqa: E402
from app.rag.ingestion.service import IngestionService  # noqa: E402
from app.rag.retrieval.embeddings import EmbeddingModel  # noqa: E402
from app.rag.retrieval.vector_store import LocalVectorStore  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate GroundDesk support citations, escalation and follow-up context."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("benchmarks/datasets/grounddesk_support_v1.json"),
    )
    parser.add_argument("--sample-dir", type=Path, default=Path("sample_corpus"))
    parser.add_argument(
        "--modes",
        default="hybrid",
        help="Comma-separated retrieval modes: sparse,dense,hybrid,adaptive,planned.",
    )
    parser.add_argument(
        "--embedding-provider",
        choices=("hashing", "sentence-transformers", "gemini"),
        default="hashing",
    )
    parser.add_argument("--embedding-model", default="hashing")
    parser.add_argument("--embedding-dimensions", default="384")
    parser.add_argument(
        "--generation-provider",
        choices=("template", "gemini"),
        default="template",
    )
    parser.add_argument("--generation-model", default="gemini-2.5-flash")
    parser.add_argument(
        "--generation-fallback-models",
        default="gemini-2.5-flash-lite",
        help="Comma-separated Gemini models used after primary quota/availability failure.",
    )
    parser.add_argument(
        "--query-planner-provider",
        choices=("off", "gemini"),
        default="off",
        help="Use gemini only with --modes planned; it adds one model request per query.",
    )
    parser.add_argument("--query-planner-model", default="gemini-2.5-flash")
    parser.add_argument("--gemini-generation-max-attempts", type=int, default=5)
    parser.add_argument("--gemini-generation-retry-base-seconds", type=float, default=2.0)
    parser.add_argument(
        "--gemini-generation-request-delay-seconds",
        type=float,
        default=1.0,
        help="Delay after successful Gemini generations to reduce burst traffic during evaluation.",
    )
    parser.add_argument(
        "--gemini-embedding-request-delay-seconds",
        type=float,
        default=1.1,
        help="Delay after Gemini embedding API requests during evaluation.",
    )
    parser.add_argument("--gemini-embedding-max-attempts", type=int, default=5)
    parser.add_argument("--gemini-embedding-retry-base-seconds", type=float, default=2.0)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--conversation-context-turns", type=int, default=4)
    parser.add_argument(
        "--allow-provider-api-calls",
        action="store_true",
        help="Required when using Gemini embeddings or generation.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/grounddesk_support_eval.json"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("results/grounddesk_support_eval.md"),
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Ignore/remove a matching partial checkpoint and start the evaluation again.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if (
        args.embedding_provider == "gemini"
        or args.generation_provider == "gemini"
        or args.query_planner_provider == "gemini"
    ) and not args.allow_provider_api_calls:
        raise SystemExit(
            "Gemini mode sends the demo corpus/questions to the provider and uses API "
            "quota. Re-run with --allow-provider-api-calls after confirming this is intended."
        )
    modes = tuple(item.strip().lower() for item in args.modes.split(",") if item.strip())
    invalid_modes = set(modes) - {"sparse", "dense", "hybrid", "adaptive", "planned"}
    if invalid_modes:
        raise SystemExit(f"Unsupported retrieval modes: {', '.join(sorted(invalid_modes))}")
    if "planned" in modes and args.query_planner_provider != "gemini":
        raise SystemExit(
            "The planned retrieval mode requires --query-planner-provider gemini. "
            "Use hybrid for the no-provider baseline."
        )
    dimensions = tuple(
        int(value.strip())
        for value in args.embedding_dimensions.split(",")
        if value.strip()
    )
    fallback_models = tuple(
        value.strip()
        for value in args.generation_fallback_models.split(",")
        if value.strip()
    )
    if not 1 <= args.top_k <= 10:
        raise SystemExit("--top-k must be between 1 and 10.")

    dataset = load_support_dataset(args.dataset)
    if args.generation_provider == "gemini":
        print(
            f"Gemini generation evaluation requires {len(dataset.cases)} primary "
            "answer requests. If your per-model free-tier quota is lower, this "
            "run will checkpoint and must be resumed after quota availability resets."
        )
    if "planned" in modes:
        print(
            f"Structured planning adds {len(dataset.cases)} Gemini planning requests "
            "for the planned strategy, in addition to any Gemini answer generation."
        )
    embeddings = EmbeddingModel(
        args.embedding_model,
        provider=args.embedding_provider,
        mrl_dimensions=dimensions,
        request_delay_seconds=(
            args.gemini_embedding_request_delay_seconds
            if args.embedding_provider == "gemini"
            else 0.0
        ),
        max_attempts=args.gemini_embedding_max_attempts,
        retry_base_seconds=args.gemini_embedding_retry_base_seconds,
    )
    signature = _checkpoint_signature(args, modes, dimensions)
    checkpoint_path = args.output.with_name(f"{args.output.stem}.partial.json")
    if args.no_resume:
        checkpoint_path.unlink(missing_ok=True)
    checkpoint = _load_checkpoint(checkpoint_path, signature)

    with tempfile.TemporaryDirectory(prefix="grounddesk-support-eval-") as tmp_dir:
        settings = Settings(
            data_dir=Path(tmp_dir) / "data",
            sample_dir=args.sample_dir,
            embedding_model=args.embedding_model,
            embedding_provider=args.embedding_provider,
            embedding_dimensions=dimensions,
            gemini_embedding_max_attempts=args.gemini_embedding_max_attempts,
            gemini_embedding_retry_base_seconds=args.gemini_embedding_retry_base_seconds,
            generation_provider=args.generation_provider,
            generation_model=args.generation_model,
            generation_fallback_models=fallback_models,
            gemini_generation_max_attempts=args.gemini_generation_max_attempts,
            gemini_generation_retry_base_seconds=args.gemini_generation_retry_base_seconds,
            gemini_generation_request_delay_seconds=(
                args.gemini_generation_request_delay_seconds
                if args.generation_provider == "gemini"
                else 0.0
            ),
            conversation_context_turns=args.conversation_context_turns,
            query_planner_provider=args.query_planner_provider,
            query_planner_model=args.query_planner_model,
            vector_store_backend="local",
            retrieval_mode="hybrid",
            adaptive_retrieval_enabled=False,
            final_reranker="lexical",
        )
        store = LocalVectorStore(settings.index_dir)
        ingestion = IngestionService(settings, embeddings, store)
        documents = ingestion.ingest_sample_corpus(
            metadata={"workspace_id": settings.default_workspace_id}
        )
        if not documents:
            raise SystemExit(f"No source documents found under {args.sample_dir}.")
        if (
            args.embedding_provider == "gemini" and embeddings.backend != "gemini"
        ):
            raise SystemExit(
                "Gemini embedding backend was requested but unavailable; evaluation aborted."
            )
        if (
            args.embedding_provider == "sentence-transformers"
            and embeddings.backend != "sentence-transformers"
        ):
            raise SystemExit(
                "Sentence-transformer backend was requested but unavailable; evaluation aborted."
            )
        runs = []
        for mode in modes:
            mode_settings = replace(
                settings,
                retrieval_mode=mode,
                adaptive_retrieval_enabled=mode == "adaptive",
            )
            agent = SupportAgent(mode_settings, embeddings, store)
            completed = checkpoint["completed_results"].setdefault(mode, {})

            def checkpoint_case(result: dict, *, completed=completed) -> None:
                completed[result["case_id"]] = result
                _write_json_atomic(checkpoint_path, checkpoint)
                print(
                    f"Completed {mode}: {len(completed)}/{len(dataset.cases)} cases "
                    f"(checkpoint: {checkpoint_path})"
                )

            try:
                run = evaluate_support_dataset(
                    dataset,
                    agent=agent,
                    top_k=args.top_k,
                    force_template=args.generation_provider == "template",
                    completed_results=completed,
                    on_case_completed=checkpoint_case,
                )
            except Exception as exc:
                print(
                    f"Evaluation interrupted. Completed cases are saved in {checkpoint_path}. "
                    "Re-run the same command to resume.",
                    file=sys.stderr,
                )
                if "GenerateRequestsPerDayPerProjectPerModel" in str(exc):
                    raise SystemExit(
                        "Gemini generation daily/per-model free-tier quota is exhausted. "
                        "The completed checkpoint is safe. Re-run this same command after "
                        "the quota resets; immediate retries will not complete this run."
                    ) from None
                raise
            run["strategy"] = f"{mode}+lexical"
            runs.append(run)

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "configuration": {
            "sample_dir": str(args.sample_dir),
            "embedding_provider": args.embedding_provider,
            "embedding_model": args.embedding_model,
            "embedding_backend": embeddings.backend,
            "embedding_dimensions": list(dimensions),
            "generation_provider": args.generation_provider,
            "generation_model": args.generation_model,
            "generation_fallback_models": list(fallback_models),
            "query_planner_provider": args.query_planner_provider,
            "query_planner_model": args.query_planner_model,
            "conversation_context_turns": args.conversation_context_turns,
            "gemini_generation_max_attempts": args.gemini_generation_max_attempts,
            "gemini_generation_retry_base_seconds": args.gemini_generation_retry_base_seconds,
            "gemini_generation_request_delay_seconds": args.gemini_generation_request_delay_seconds,
            "gemini_embedding_request_delay_seconds": args.gemini_embedding_request_delay_seconds,
            "gemini_embedding_max_attempts": args.gemini_embedding_max_attempts,
            "gemini_embedding_retry_base_seconds": args.gemini_embedding_retry_base_seconds,
        },
        "runs": runs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    markdown = "\n".join(
        [
            "# GroundDesk Product-Specific Evaluation",
            "",
            f"- **Embedding backend/model:** `{embeddings.backend}` / `{args.embedding_model}`",
            f"- **Generation:** `{args.generation_provider}` / `{args.generation_model}`",
            "",
            *[
                f"## Strategy: `{run['strategy']}`\n\n"
                f"{report_as_markdown(run).replace('# GroundDesk Support Evaluation Report', '### Results', 1)}"
                for run in runs
            ],
        ]
    )
    args.report.write_text(markdown + "\n", encoding="utf-8")
    checkpoint_path.unlink(missing_ok=True)
    print(markdown)
    print(f"JSON details: {args.output}")
    print(f"Markdown report: {args.report}")


def _checkpoint_signature(args, modes: tuple[str, ...], dimensions: tuple[int, ...]) -> dict:
    return {
        "dataset": str(args.dataset),
        "sample_dir": str(args.sample_dir),
        "modes": list(modes),
        "embedding_provider": args.embedding_provider,
        "embedding_model": args.embedding_model,
        "embedding_dimensions": list(dimensions),
        "gemini_embedding_max_attempts": args.gemini_embedding_max_attempts,
        "gemini_embedding_retry_base_seconds": args.gemini_embedding_retry_base_seconds,
        "generation_provider": args.generation_provider,
        "generation_model": args.generation_model,
        "generation_fallback_models": args.generation_fallback_models,
        "query_planner_provider": args.query_planner_provider,
        "query_planner_model": args.query_planner_model,
        "top_k": args.top_k,
        "conversation_context_turns": args.conversation_context_turns,
        "gemini_generation_max_attempts": args.gemini_generation_max_attempts,
        "gemini_generation_retry_base_seconds": args.gemini_generation_retry_base_seconds,
        "gemini_generation_request_delay_seconds": args.gemini_generation_request_delay_seconds,
        "gemini_embedding_request_delay_seconds": args.gemini_embedding_request_delay_seconds,
        "gemini_embedding_max_attempts": args.gemini_embedding_max_attempts,
        "gemini_embedding_retry_base_seconds": args.gemini_embedding_retry_base_seconds,
    }


def _load_checkpoint(path: Path, signature: dict) -> dict:
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("signature") == signature:
            print(f"Resuming completed evaluation cases from {path}")
            return payload
        raise SystemExit(
            f"Partial checkpoint {path} was created with different arguments. "
            "Use --no-resume to discard it or choose a different --output path."
        )
    return {"signature": signature, "completed_results": {}}


def _write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


if __name__ == "__main__":
    main()

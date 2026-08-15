from fastapi import APIRouter, Depends

from app.api.dependencies import (
    get_agent,
    get_app_settings,
    get_embedding_model,
    get_vector_store,
    require_admin,
)
from app.evals import EVALUATION_SCOPE
from app.evals.answers import run_answer_quality_evals
from app.evals.golden_set import run_evals
from app.evals.retrieval import run_retrieval_evals
from app.evals.support_dataset import evaluate_support_dataset, load_support_dataset
from app.evals.synthetic import generate_synthetic_eval_dataset
from app.evals.variants import compare_retrieval_variants
from app.infrastructure.config import Settings

router = APIRouter(prefix="/evals", tags=["evals"])


@router.post("/run")
def evals(_: None = Depends(require_admin), agent=Depends(get_agent)):
    return run_evals(agent)


@router.post("/retrieval")
def retrieval_evals(
    _: None = Depends(require_admin),
    agent=Depends(get_agent),
    embedding_model=Depends(get_embedding_model),
):
    return run_retrieval_evals(agent.retriever, embedding_model)


@router.post("/answers")
def answer_evals(_: None = Depends(require_admin), agent=Depends(get_agent)):
    return run_answer_quality_evals(agent)


@router.post("/synthetic")
def synthetic_evals(_: None = Depends(require_admin), store=Depends(get_vector_store)):
    return generate_synthetic_eval_dataset(store.list_chunks(EVALUATION_SCOPE))


@router.post("/variants")
def retrieval_variant_evals(_: None = Depends(require_admin), agent=Depends(get_agent)):
    return compare_retrieval_variants(agent)


@router.post("/support")
def support_product_evals(
    _: None = Depends(require_admin),
    agent=Depends(get_agent),
    settings: Settings = Depends(get_app_settings),
):
    return evaluate_support_dataset(
        load_support_dataset(settings.support_eval_dataset_path),
        agent=agent,
        force_template=True,
    )

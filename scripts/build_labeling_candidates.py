#!/usr/bin/env python3
"""Calculate policy/post similarity and create a private labeling worksheet."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import numpy as np

from analysis_pipeline import (
    LABELING_FIELDS,
    SIMILARITY_FIELDS,
    calculate_similarity_rows,
    read_processed_posts,
    select_labeling_candidates,
    sha256_file,
    write_csv,
)
from policy_catalog import select_policy_rows


class SentenceTransformerEncoder:
    def __init__(
        self, model_name: str, revision: str, device: str | None, batch_size: int
    ) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise RuntimeError(
                "sentence-transformers is required; install requirements-analysis.txt"
            ) from error
        self.model = SentenceTransformer(model_name, revision=revision, device=device)
        self.batch_size = batch_size

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        return np.asarray(
            self.model.encode(
                list(texts),
                batch_size=self.batch_size,
                convert_to_numpy=True,
                show_progress_bar=True,
            )
        )


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build similarity results and a human-labeling worksheet."
    )
    parser.add_argument("--analysis-config", type=Path, required=True)
    parser.add_argument("--posts", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--policy-set")
    parser.add_argument("--device", help="Sentence Transformers device, e.g. cpu or cuda")
    parser.add_argument(
        "--batch-size", type=int, default=32,
        help="Embedding batch size; changes execution speed, not the analysis rules",
    )
    parser.add_argument(
        "--model",
        help="Override embedding model from the analysis config (requires --revision)",
    )
    parser.add_argument(
        "--revision",
        help="Override embedding revision from the analysis config (requires --model)",
    )
    args = parser.parse_args()
    if (args.model is None) != (args.revision is None):
        parser.error("--model and --revision must be specified together")
    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")
    config = json.loads(args.analysis_config.read_text(encoding="utf-8"))
    policy_definition = config["policy"]
    policy_config_path = Path(policy_definition["config"])
    if not policy_config_path.is_absolute():
        policy_config_path = (args.analysis_config.parent / policy_config_path).resolve()
    policy_set = args.policy_set or policy_definition["trial_set"]
    _, policy_rows, policy_config = select_policy_rows(policy_config_path, policy_set)
    posts = read_processed_posts(args.posts)
    embedding = config["embedding"]
    run_embedding = {
        **embedding,
        "model": args.model or embedding["model"],
        "revision": args.revision or embedding["revision"],
    }
    encoder = SentenceTransformerEncoder(
        run_embedding["model"], run_embedding["revision"], args.device, args.batch_size
    )
    similarity_rows = calculate_similarity_rows(
        policy_rows, posts, policy_set, policy_config["comparison_text_fields"],
        embedding["query_prefix"], embedding["document_prefix"], encoder,
    )
    sampling = config["candidate_sampling"]
    labeling_rows = select_labeling_candidates(
        similarity_rows,
        top_k=sampling["top_k"],
        middle_sample_size=sampling["middle_sample_size"],
        low_sample_size=sampling["low_sample_size"],
        random_seed=sampling["random_seed"],
        middle_start=sampling["middle_percentile_start"],
        middle_end=sampling["middle_percentile_end"],
        low_start=sampling["low_percentile_start"],
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.output_dir.chmod(0o700)
    write_csv(args.output_dir / "similarity_all.csv", SIMILARITY_FIELDS, similarity_rows)
    write_csv(args.output_dir / "labeling_candidates.csv", LABELING_FIELDS, labeling_rows)
    metadata = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "policy_set": policy_set,
        "policy_ids": [row["policy_id"] for row in policy_rows],
        "post_count": len(posts),
        "similarity_pair_count": len(similarity_rows),
        "labeling_candidate_count": len(labeling_rows),
        "input_posts_sha256": sha256_file(args.posts),
        "analysis_config_sha256": sha256_file(args.analysis_config),
        "model": run_embedding,
        "sampling": sampling,
        "human_labeling": config["human_labeling"],
        "analysis_views": config["analysis_views"],
        "runtime": {
            "python": platform.python_version(),
            "numpy": package_version("numpy"),
            "sentence_transformers": package_version("sentence-transformers"),
            "transformers": package_version("transformers"),
            "torch": package_version("torch"),
        },
        "execution": {"device": args.device, "batch_size": args.batch_size},
    }
    metadata_path = args.output_dir / "run_metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    metadata_path.chmod(0o600)
    print(
        f"wrote {len(similarity_rows)} pairs and {len(labeling_rows)} "
        f"labeling candidates to {args.output_dir}"
    )


if __name__ == "__main__":
    main()

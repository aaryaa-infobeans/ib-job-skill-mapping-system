"""
Setup script for the google/embedding-gemma-300m embedding model (CR-EMB-002).

What this script does
---------------------
1. Check Python dependencies (transformers, torch, huggingface_hub).
2. Resolve the best available option in priority order:
     A. Already cached locally (HuggingFace cache or GEMMA_MODEL_PATH).
     B. Download from HuggingFace (public or with HF_TOKEN for gated access).
     C. Offer a compatible public fallback (sentence-transformers/all-mpnet-base-v2,
        also 768-dim) for environments that cannot access the Gemma model.
3. Smoke-test: load tokenizer + model, embed one sentence, verify shape=(768,).
4. Print the .env snippet to paste (GEMMA_MODEL_PATH=<path>).

Usage
-----
    # Basic (tries HuggingFace without a token)
    python scripts/setup_gemma_model.py

    # With a HuggingFace token (required for gated/private models)
    python scripts/setup_gemma_model.py --hf-token hf_xxxxxxxxxxxx

    # Point at a model you already downloaded
    python scripts/setup_gemma_model.py --local-path /path/to/model

    # Use fallback without prompting
    python scripts/setup_gemma_model.py --use-fallback

Environment variables honoured
-------------------------------
    HF_TOKEN              HuggingFace access token (same as --hf-token)
    GEMMA_MODEL_PATH      If set, script validates this path/id first
    HF_HOME               HuggingFace cache root (default: ~/.cache/huggingface)
"""

import argparse
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TARGET_MODEL_ID = "google/embedding-gemma-300m"
FALLBACK_MODEL_ID = "sentence-transformers/all-mpnet-base-v2"  # public, 768-dim
EXPECTED_DIM = 768

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok(msg: str) -> None:
    print(f"  [ OK ]  {msg}")


def _info(msg: str) -> None:
    print(f"  [ -- ]  {msg}")


def _warn(msg: str) -> None:
    print(f"  [ !! ]  {msg}", file=sys.stderr)


def _fail(msg: str) -> None:
    print(f"  [FAIL]  {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Step 1 – dependency check
# ---------------------------------------------------------------------------


def check_dependencies() -> None:
    print("\n=== Step 1: Checking dependencies ===")
    missing = []
    for pkg in ["torch", "transformers", "huggingface_hub", "numpy"]:
        try:
            __import__(pkg)
            _ok(pkg)
        except ImportError:
            _warn(f"{pkg} not found")
            missing.append(pkg)

    if missing:
        _fail(
            f"Install missing packages:\n"
            f"    pip install {' '.join(missing)}\n"
            f"  Or install all CR-EMB-002 deps:\n"
            f"    pip install 'transformers>=4.40' torch 'sentencepiece>=0.2.0' huggingface_hub"
        )


# ---------------------------------------------------------------------------
# Step 2 – resolve existing cache / env override
# ---------------------------------------------------------------------------


def resolve_cached_path() -> str | None:
    """
    Return a model id / path that's already usable without a download,
    or None if nothing is ready yet.
    """
    # 1. Explicit env var / local path override
    env_path = os.environ.get("GEMMA_MODEL_PATH", "").strip()
    if env_path:
        p = Path(env_path)
        if p.is_dir() and (p / "config.json").exists():
            _ok(f"Found local model at GEMMA_MODEL_PATH: {env_path}")
            return env_path
        else:
            _warn(f"GEMMA_MODEL_PATH={env_path} set but config.json not found there; ignoring.")

    # 2. HuggingFace disk cache
    try:
        from huggingface_hub import try_to_load_from_cache, _CACHED_NO_EXIST

        cached = try_to_load_from_cache(TARGET_MODEL_ID, "config.json")
        if cached and cached is not _CACHED_NO_EXIST:
            cache_dir = Path(cached).parent
            _ok(f"Model already in HuggingFace cache: {cache_dir}")
            return TARGET_MODEL_ID   # transformers knows how to load from cache
    except Exception:
        pass  # older huggingface_hub versions may not have try_to_load_from_cache

    return None


# ---------------------------------------------------------------------------
# Step 3 – download from HuggingFace
# ---------------------------------------------------------------------------


def download_model(hf_token: str | None) -> str:
    """
    Attempt to download TARGET_MODEL_ID.
    Returns the model id to use (from cache after download).
    Raises on failure.
    """
    from huggingface_hub import snapshot_download, HfApi
    import requests

    _info(f"Attempting to download {TARGET_MODEL_ID} from HuggingFace …")

    # Check model visibility before attempting download
    api = HfApi(token=hf_token)
    try:
        info = api.model_info(TARGET_MODEL_ID, token=hf_token)
        gated = getattr(info, "gated", False)
        if gated:
            _info(f"Model is gated (requires accepting terms on huggingface.co/{TARGET_MODEL_ID})")
            if not hf_token:
                raise PermissionError(
                    "Model is gated but no HF_TOKEN provided. "
                    "Accept the terms at huggingface.co and pass --hf-token hf_xxx "
                    "or set the HF_TOKEN environment variable."
                )
    except Exception as check_exc:
        if "404" in str(check_exc) or "does not exist" in str(check_exc).lower():
            raise FileNotFoundError(
                f"Model '{TARGET_MODEL_ID}' was not found on HuggingFace.\n"
                f"  • Check that the model ID is correct at https://huggingface.co/{TARGET_MODEL_ID}\n"
                f"  • If the model is private, provide --hf-token\n"
                f"  • Re-run with --use-fallback to use a compatible public model instead"
            )
        raise

    local_dir = snapshot_download(
        repo_id=TARGET_MODEL_ID,
        token=hf_token,
        ignore_patterns=["*.msgpack", "flax_model*", "tf_model*", "rust_model*"],
    )
    _ok(f"Downloaded to: {local_dir}")
    return TARGET_MODEL_ID  # load from HF cache by model id


# ---------------------------------------------------------------------------
# Step 4 – download fallback model
# ---------------------------------------------------------------------------


def download_fallback(hf_token: str | None) -> str:
    """Download the public fallback model and return its cache path."""
    from huggingface_hub import snapshot_download

    _info(f"Downloading fallback model: {FALLBACK_MODEL_ID} …")
    local_dir = snapshot_download(
        repo_id=FALLBACK_MODEL_ID,
        token=hf_token,
        ignore_patterns=["*.msgpack", "flax_model*", "tf_model*"],
    )
    _ok(f"Fallback model downloaded to: {local_dir}")
    return local_dir


# ---------------------------------------------------------------------------
# Step 5 – smoke test
# ---------------------------------------------------------------------------


def smoke_test(model_id_or_path: str) -> None:
    """Load model + tokenizer, embed one sentence, assert shape=(768,)."""
    import numpy as np
    import torch
    from transformers import AutoModel, AutoTokenizer

    _info(f"Loading tokenizer from '{model_id_or_path}' …")
    tokenizer = AutoTokenizer.from_pretrained(model_id_or_path)
    _info("Loading model …")
    # Suppress torch_dtype deprecation warning
    import warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*torch_dtype.*deprecated.*", category=FutureWarning)
        model = AutoModel.from_pretrained(model_id_or_path, torch_dtype=torch.float32)
    model.eval()

    sample = "Software engineer with 5 years of Python and cloud experience."
    encoded = tokenizer(sample, return_tensors="pt", truncation=True, max_length=512)

    with torch.no_grad():
        out = model(**encoded)

    # Mean pooling
    last_hidden = out.last_hidden_state  # (1, seq, hidden)
    mask = encoded["attention_mask"].unsqueeze(-1).expand(last_hidden.size()).float()
    pooled = (last_hidden.float() * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
    vec = pooled[0].cpu().numpy()

    # L2 normalise
    norm = np.linalg.norm(vec)
    if norm > 1e-9:
        vec = vec / norm

    if vec.shape != (EXPECTED_DIM,):
        _fail(
            f"Unexpected embedding dimension: got {vec.shape}, expected ({EXPECTED_DIM},).\n"
            f"  This model is not compatible with the CR-EMB-002 pipeline.\n"
            f"  Re-run with --use-fallback for a guaranteed-compatible model."
        )

    _ok(f"Embedding shape: {vec.shape} ✓")
    _ok(f"L2 norm: {float(np.linalg.norm(vec)):.6f} (expected ≈ 1.0) ✓")


# ---------------------------------------------------------------------------
# Step 6 – write / update .env
# ---------------------------------------------------------------------------


def update_env_file(model_path: str) -> None:
    """
    Upsert GEMMA_MODEL_PATH in .env.
    If the key already exists, replace it; otherwise append.
    """
    key = "GEMMA_MODEL_PATH"
    new_line = f'{key}={model_path}\n'

    if ENV_FILE.exists():
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines(keepends=True)
        replaced = False
        for i, line in enumerate(lines):
            if line.startswith(f"{key}=") or line.startswith(f"{key} ="):
                lines[i] = new_line
                replaced = True
                break
        if not replaced:
            # Append under the CR-EMB-002 section if it exists, else at EOF
            insert_idx = next(
                (i for i, l in enumerate(lines) if "CR-EMB-002" in l or "embedding" in l.lower()),
                len(lines),
            )
            lines.insert(insert_idx + 1, new_line)
        ENV_FILE.write_text("".join(lines), encoding="utf-8")
        _ok(f"Updated {ENV_FILE}: {key}={model_path}")
    else:
        _warn(f".env not found at {ENV_FILE}; skipping auto-update.")
        print(f"\n  Add this to your .env manually:\n\n    {key}={model_path}\n")


# ---------------------------------------------------------------------------
# Step 7 – print summary
# ---------------------------------------------------------------------------


def print_summary(model_path: str, used_fallback: bool) -> None:
    print("\n" + "=" * 60)
    if used_fallback:
        print(f"  Model ready  (fallback: {FALLBACK_MODEL_ID})")
        print()
        print("  NOTE: The fallback model is compatible with the 768-dim")
        print(f"  pipeline but is NOT {TARGET_MODEL_ID}.")
        print("  Replace with the real model when access is available.")
    else:
        print(f"  Model ready  ({TARGET_MODEL_ID})")
    print()
    print("  .env entry set:")
    print(f"    GEMMA_MODEL_PATH={model_path}")
    print()
    print("  Run the embed phase:")
    print("    python -m app.cron ingest-embed")
    print("    python -m app.cron.main embed --force   # embed only")
    print("=" * 60 + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download and configure the Gemma embedding model for CR-EMB-002."
    )
    parser.add_argument(
        "--hf-token",
        metavar="TOKEN",
        default=os.environ.get("HF_TOKEN", ""),
        help="HuggingFace access token (required for gated models). "
             "Alternatively set the HF_TOKEN env var.",
    )
    parser.add_argument(
        "--local-path",
        metavar="PATH",
        default="",
        help="Path to an already-downloaded model directory. Skips the download step.",
    )
    parser.add_argument(
        "--use-fallback",
        action="store_true",
        help=f"Skip the Gemma model and use {FALLBACK_MODEL_ID} instead "
             f"(public, 768-dim, no auth required).",
    )
    parser.add_argument(
        "--no-env-update",
        action="store_true",
        help="Do not write to .env; only print the required snippet.",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  CR-EMB-002 — Gemma Embedding Model Setup")
    print("=" * 60)

    check_dependencies()

    used_fallback = False

    # --- resolve model path ---
    print("\n=== Step 2: Resolving model ===")

    if args.local_path:
        local = Path(args.local_path)
        if not (local / "config.json").exists():
            _fail(f"--local-path '{args.local_path}' does not contain config.json")
        model_path = str(local.resolve())
        _ok(f"Using provided local path: {model_path}")

    elif args.use_fallback:
        _info(f"--use-fallback set; using {FALLBACK_MODEL_ID}")
        print("\n=== Step 3: Downloading fallback model ===")
        model_path = download_fallback(args.hf_token or None)
        used_fallback = True

    else:
        cached = resolve_cached_path()
        if cached:
            model_path = cached
        else:
            print("\n=== Step 3: Downloading model ===")
            try:
                model_path = download_model(args.hf_token or None)
            except (FileNotFoundError, PermissionError) as exc:
                print(f"\n  {exc}\n")
                answer = input(
                    f"  Download fallback model ({FALLBACK_MODEL_ID}) instead? [y/N] "
                ).strip().lower()
                if answer != "y":
                    _fail("Aborted. Re-run with --use-fallback or --hf-token.")
                model_path = download_fallback(args.hf_token or None)
                used_fallback = True

    # --- smoke test ---
    print("\n=== Step 4: Smoke test ===")
    smoke_test(model_path)

    # --- update .env ---
    print("\n=== Step 5: Updating .env ===")
    if args.no_env_update:
        _info("--no-env-update set; skipping .env write.")
    else:
        update_env_file(model_path)

    print_summary(model_path, used_fallback)


if __name__ == "__main__":
    main()

"""SQ3 divergence catalog.

Implements §8 of ``phase_5_sq3_methodology.md``. A pair is a divergence
case if its ``|rating_in_unit_interval - cosine|`` exceeds the 90th
percentile of that quantity across the rated set, where
``rating_in_unit_interval = rating / 3.0`` (the rating scale is 0-3).

The 90th-percentile threshold is fixed; the resulting divergence count
is data-determined.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_THRESHOLD_PERCENTILE = 90.0


def _saldo_relation_summary(
    saldo_graph,
    target: str,
    response: str,
    max_hops: int = 3,
) -> str:
    """Return a short SALDO-relation summary string for a (target, response) pair.

    Uses ``SaldoGraph``'s public interface: ``lookup``,
    ``primary_descriptor``, and ``path_length``.

    Possible return values:

    * ``mother(t→r)`` — response sense is the primary descriptor of a
      target sense (``target`` is a hyponym of ``response``).
    * ``mother(r→t)`` — target sense is the primary descriptor of a
      response sense (``response`` is a hyponym of ``target``).
    * ``m-sibling`` — target and response share a primary descriptor.
    * ``near`` — both in SALDO and a path of length ``≤ max_hops`` exists
      that does not match any of the more specific relations above.
    * ``far`` — both in SALDO but no path within ``max_hops`` hops.
    * ``oov(t)`` / ``oov(r)`` / ``oov(both)`` — at least one side OOV.
    """
    t_senses = saldo_graph.lookup(target)
    r_senses = saldo_graph.lookup(response)
    if not t_senses and not r_senses:
        return "oov(both)"
    if not t_senses:
        return "oov(t)"
    if not r_senses:
        return "oov(r)"

    t_parents = {saldo_graph.primary_descriptor(s) for s in t_senses}
    r_parents = {saldo_graph.primary_descriptor(s) for s in r_senses}
    t_parents.discard(None)
    r_parents.discard(None)

    if t_parents & set(r_senses):
        return "mother(t→r)"
    if r_parents & set(t_senses):
        return "mother(r→t)"
    if t_parents & r_parents:
        return "m-sibling"

    best = None
    for ts in t_senses:
        for rs in r_senses:
            pl = saldo_graph.path_length(ts, rs)
            if pl is not None and (best is None or pl < best):
                best = pl
    if best is None:
        return "far"
    if best <= max_hops:
        return "near"
    return "far"


def compute_divergence_catalog(
    ratings: pd.DataFrame,
    sampled_pairs: pd.DataFrame,
    primary_model_cosines: pd.DataFrame,
    saldo_graph,
    threshold_percentile: float = DEFAULT_THRESHOLD_PERCENTILE,
) -> pd.DataFrame:
    """Return a divergence catalog (one row per pair, divergence cases flagged).

    Disagreement is computed as ``|rating/3 - cosine_sim|`` on the inner
    join of ``ratings`` and ``primary_model_cosines`` on ``pair_id``.
    Pairs with ``disagreement`` strictly greater than the
    ``threshold_percentile``-th percentile of disagreement are tagged
    ``is_divergence_case=True``.

    Returned columns:
        ``pair_id, target, response, rater_mean_rating,
        cosine_sim_primary_model, disagreement, rater_category,
        is_compound, saldo_relation_summary, is_divergence_case``.
    """
    required_ratings = {"pair_id", "rating", "category", "is_compound"}
    missing = required_ratings - set(ratings.columns)
    if missing:
        raise KeyError(f"ratings missing columns: {missing}")
    required_pairs = {"pair_id", "target", "response"}
    missing_p = required_pairs - set(sampled_pairs.columns)
    if missing_p:
        raise KeyError(f"sampled_pairs missing columns: {missing_p}")
    if not {"pair_id", "cosine_sim"}.issubset(primary_model_cosines.columns):
        raise KeyError("primary_model_cosines missing pair_id/cosine_sim")

    rating_cols = ratings[["pair_id", "rating", "category", "is_compound"]]
    base = rating_cols.merge(
        sampled_pairs[["pair_id", "target", "response"]], on="pair_id", how="inner"
    ).merge(
        primary_model_cosines[["pair_id", "cosine_sim"]], on="pair_id", how="inner"
    )
    rating_unit = base["rating"].astype(float) / 3.0
    cosine = base["cosine_sim"].astype(float)
    disagreement = (rating_unit - cosine).abs()

    if len(disagreement) == 0:
        threshold = float("nan")
        is_div = pd.Series([], dtype=bool)
    else:
        threshold = float(np.percentile(disagreement, threshold_percentile))
        is_div = disagreement > threshold

    saldo_summary = [
        _saldo_relation_summary(saldo_graph, str(t), str(r))
        for t, r in zip(base["target"], base["response"])
    ]

    catalog = pd.DataFrame(
        {
            "pair_id": base["pair_id"].to_numpy(),
            "target": base["target"].to_numpy(),
            "response": base["response"].to_numpy(),
            "rater_mean_rating": base["rating"].to_numpy(),
            "cosine_sim_primary_model": cosine.to_numpy(),
            "disagreement": disagreement.to_numpy(),
            "rater_category": base["category"].to_numpy(),
            "is_compound": base["is_compound"].to_numpy(),
            "saldo_relation_summary": saldo_summary,
            "is_divergence_case": is_div.to_numpy(),
        }
    )
    catalog = catalog.sort_values("disagreement", ascending=False).reset_index(drop=True)
    catalog.attrs["threshold_percentile"] = threshold_percentile
    catalog.attrs["threshold_value"] = threshold
    return catalog

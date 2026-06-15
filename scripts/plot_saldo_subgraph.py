"""Render a local SALDO neighbourhood around a focal written form.

Designed for the thesis figure illustrating SALDO's mother / m-sibling /
optional father relations, using a real example from the SQ3 divergence
catalog (default focal: ``kringla``).

Usage
-----

    python scripts/plot_saldo_subgraph.py \\
        --focal kringla \\
        --highlight kex --highlight bakverk \\
        --output thesis/figures/saldo_kringla_subgraph.pdf

Add ``--show-father`` to draw the secondary-descriptor edge of the focal
sense, if one exists.

The script depends only on the existing ``SaldoGraph`` public API
(Phase A artefact) and matplotlib. No new repository dependencies.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch

# Make the script runnable from any cwd within the repo.
_PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ / "src"))

from thesis_project.lexical.saldo import SaldoGraph  # noqa: E402

# ──────────────────────────────────────────────────────────────────────────
# Styling
# ──────────────────────────────────────────────────────────────────────────

FOCAL_COLOR = "#4878A8"      # muted slate blue
HIGHLIGHT_COLOR = "#B85450"  # muted brick red
SIBLING_COLOR = "#9A9A9A"    # neutral grey
ANCESTOR_COLOR = "#6F9F70"   # muted sage green
FATHER_COLOR = "#8A6FA8"     # muted dusty purple
EDGE_COLOR = "#333333"       # near-black, softer than pure black

MOTHER_EDGE = dict(
    arrowstyle="-|>", color=EDGE_COLOR, linewidth=1.0, linestyle="-",
    mutation_scale=11, connectionstyle="arc3,rad=0.0",
)
FATHER_EDGE = dict(
    arrowstyle="-|>", color=FATHER_COLOR, linewidth=1.0, linestyle="--",
    mutation_scale=11, connectionstyle="arc3,rad=0.15",
)


# ──────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--pickle", type=Path, default=Path("data/lexical/saldo.pkl"),
        help="Path to the SaldoGraph pickle (Phase A artefact).",
    )
    p.add_argument(
        "--focal", type=str, default="kringla",
        help="Written form of the focal node (default: kringla).",
    )
    p.add_argument(
        "--sense-index", type=int, default=0,
        help="Which sense of a polysemous focal to use (0-indexed).",
    )
    p.add_argument(
        "--output", type=Path,
        default=Path("thesis/figures/saldo_kringla_subgraph.pdf"),
        help="Output path for the figure.",
    )
    p.add_argument(
        "--format", choices=("pdf", "png"), default="pdf",
        help="Output format (default: pdf).",
    )
    p.add_argument(
        "--show-father", action="store_true",
        help="Include the focal's secondary-descriptor (father) edge "
             "if one exists. Off by default.",
    )
    p.add_argument(
        "--highlight", action="append", default=[],
        help="Additional written form(s) to mark prominently. Repeatable. "
             "If a highlighted word appears in the rendered "
             "neighbourhood (sibling or ancestor), it is drawn in the "
             "highlight colour and given priority placement among siblings.",
    )
    p.add_argument(
        "--max-siblings", type=int, default=5,
        help="Cap on m-siblings of focal that are drawn (default 5).",
    )
    p.add_argument(
        "--mother-steps", type=int, default=2,
        help="Mother-edges to walk upward from focal before collapsing "
             "the remaining path to PRIM into a dotted stub (default 2).",
    )
    p.add_argument(
        "--figsize", type=float, nargs=2, default=(8.0, 5.5),
        metavar=("W", "H"),
        help="Figure size in inches (default 8.0 5.5).",
    )
    return p.parse_args()


# ──────────────────────────────────────────────────────────────────────────
# Graph traversal helpers
# ──────────────────────────────────────────────────────────────────────────

def pick_sense(g: SaldoGraph, written_form: str, index: int) -> str:
    senses = g.lookup(written_form)
    if not senses:
        sys.exit(
            f"ERROR: '{written_form}' is not in SALDO. Check spelling, or "
            f"try a different focal."
        )
    if index >= len(senses):
        sys.exit(
            f"ERROR: '{written_form}' has {len(senses)} sense(s); "
            f"--sense-index {index} is out of range."
        )
    return senses[index]


def mother_chain(g: SaldoGraph, sense_id: str, max_steps: int) -> list[str]:
    """Return the upward chain starting at sense_id and walking mothers.

    Stops at PRIM, at depth None, or after max_steps mothers. The
    returned list always begins with sense_id itself.
    """
    chain = [sense_id]
    cur = sense_id
    for _ in range(max_steps):
        parent = g.primary_descriptor(cur)
        if parent is None:
            break
        chain.append(parent)
        if parent == "PRIM..1":
            break
        cur = parent
    return chain


def siblings_of(
    g: SaldoGraph,
    focal: str,
    max_n: int,
    must_include_forms: list[str],
) -> list[str]:
    """Return up to max_n m-siblings of focal, prioritising highlights."""
    mother = g.primary_descriptor(focal)
    if mother is None:
        return []
    pool = sorted(g.children(mother) - {focal})
    must = {w.lower() for w in must_include_forms}
    priority = [s for s in pool
                if (g.written_form(s) or "").lower() in must]
    rest = [s for s in pool if s not in priority]
    return priority + rest[: max(0, max_n - len(priority))]


def short_label(g: SaldoGraph, sense_id: str) -> str:
    if sense_id == "PRIM..1":
        return "PRIM"
    return g.written_form(sense_id) or sense_id


# ──────────────────────────────────────────────────────────────────────────
# Layout + rendering
# ──────────────────────────────────────────────────────────────────────────

def layout_positions(
    g: SaldoGraph,
    focal: str,
    chain: list[str],
    sibs: list[str],
    father: str | None,
    show_prim_stub: bool,
    highlight_lower: set[str],
) -> tuple[dict[str, tuple[float, float]], dict[str, str]]:
    """Compute (x, y) positions and display labels for every drawn node."""
    coords: dict[str, tuple[float, float]] = {}
    labels: dict[str, str] = {}

    # Ancestor stack: vertical column at x=0, focal at y=0.
    # chain[0] = focal, chain[1] = mother, chain[2] = grandmother, etc.
    chain_y_step = 1.4
    for i, sense in enumerate(chain):
        coords[sense] = (0.0, float(i) * chain_y_step)
        labels[sense] = short_label(g, sense)

    if show_prim_stub:
        top_y = float(len(chain)) * chain_y_step + 0.9
        coords["__prim_stub__"] = (0.0, top_y)
        labels["__prim_stub__"] = "PRIM"

    # Siblings: spread symmetrically around the focal at y=0. Highlighted
    # siblings get the slots closest to focal so they're easy to point at.
    if sibs:
        spacing = 2.4
        # Reorder so highlighted siblings come first
        sibs_ordered = sorted(
            sibs,
            key=lambda s: (
                (g.written_form(s) or "").lower() not in highlight_lower,
                short_label(g, s),
            ),
        )
        # Alternate left/right around focal
        for i, sense in enumerate(sibs_ordered):
            slot = (i // 2) + 1
            side = -1 if (i % 2 == 0) else 1
            coords[sense] = (side * slot * spacing, 0.0)
            labels[sense] = short_label(g, sense)

    # Father: place to upper-left of focal so it doesn't collide with the
    # mother arrow going straight up.
    if father:
        coords[father] = (-1.8, 1.4)
        labels[father] = short_label(g, father)

    return coords, labels


def node_style(
    sense: str,
    focal: str,
    father: str | None,
    chain: list[str],
    highlight_lower: set[str],
    g: SaldoGraph,
) -> dict:
    if sense in ("PRIM..1", "__prim_stub__"):
        return dict(color="black", size=180, weight="bold", italic=False)
    if sense == focal:
        return dict(color=FOCAL_COLOR, size=440, weight="bold", italic=True)
    wf = (g.written_form(sense) or "").lower()
    if wf in highlight_lower:
        return dict(color=HIGHLIGHT_COLOR, size=380, weight="bold",
                    italic=True)
    if sense in chain[1:]:
        return dict(color=ANCESTOR_COLOR, size=320, weight="normal",
                    italic=True)
    if sense == father:
        return dict(color=FATHER_COLOR, size=300, weight="normal",
                    italic=True)
    return dict(color=SIBLING_COLOR, size=260, weight="normal",
                italic=True)


def render(
    g: SaldoGraph,
    focal: str,
    chain: list[str],
    sibs: list[str],
    father: str | None,
    coords: dict[str, tuple[float, float]],
    labels: dict[str, str],
    show_prim_stub: bool,
    highlight_lower: set[str],
    focal_form: str,
    highlight_forms: list[str],
    figsize: tuple[float, float],
) -> plt.Figure:
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_aspect("equal")
    ax.axis("off")

    # Nodes
    for sense, (x, y) in coords.items():
        s = node_style(sense, focal, father, chain, highlight_lower, g)
        ax.scatter([x], [y], s=s["size"], color=s["color"],
                   zorder=3, edgecolors="white", linewidths=1.5)
        ax.text(
            x, y - 0.22, labels[sense],
            ha="center", va="top",
            fontsize=10, fontweight=s["weight"],
            style="italic" if s["italic"] else "normal",
        )

    # Mother edges along the chain (focal → mother → ...)
    for child, parent in zip(chain[:-1], chain[1:]):
        if child in coords and parent in coords:
            x1, y1 = coords[child]
            x2, y2 = coords[parent]
            ax.add_patch(FancyArrowPatch(
                (x1, y1 + 0.10), (x2, y2 - 0.10),
                zorder=2, **MOTHER_EDGE,
            ))

    # Sibling → mother edges (all siblings share the focal's mother)
    if sibs and len(chain) >= 2:
        mother = chain[1]
        mx, my = coords[mother]
        for sense in sibs:
            if sense in coords:
                sx, sy = coords[sense]
                ax.add_patch(FancyArrowPatch(
                    (sx, sy + 0.10), (mx, my - 0.10),
                    zorder=2, **MOTHER_EDGE,
                ))

    # Father edge (focal → father, dashed)
    if father and father in coords:
        focal_x, focal_y = coords[focal]
        fx, fy = coords[father]
        ax.add_patch(FancyArrowPatch(
            (focal_x, focal_y + 0.10), (fx, fy - 0.10),
            zorder=2, **FATHER_EDGE,
        ))

    # PRIM stub: dotted line from the top of the rendered chain up to PRIM
    if show_prim_stub:
        top_chain_sense = chain[-1]
        x1, y1 = coords[top_chain_sense]
        x2, y2 = coords["__prim_stub__"]
        ax.plot(
            [x1, x2], [y1 + 0.10, y2 - 0.10],
            color="black", linestyle=":", linewidth=1.0, zorder=2,
        )
        focal_depth = g.depth(focal)
        if focal_depth is not None:
            ax.text(
                x1 + 0.25, (y1 + y2) / 2,
                f"(further mother chain;\nfocal at depth {focal_depth})",
                fontsize=7, ha="left", va="center",
                color="dimgrey", style="italic",
            )

    # Legend
    legend_handles = [
        Line2D([0], [0], color="black", lw=1.2,
               label="mother (primary descriptor)"),
        Line2D([0], [0], marker="o", color="w",
               markerfacecolor=FOCAL_COLOR, markersize=10,
               label=f"focal: {focal_form}"),
        Line2D([0], [0], marker="o", color="w",
               markerfacecolor=ANCESTOR_COLOR, markersize=9,
               label="ancestor"),
        Line2D([0], [0], marker="o", color="w",
               markerfacecolor=SIBLING_COLOR, markersize=9,
               label="m-sibling"),
    ]
    if highlight_forms:
        legend_handles.append(Line2D(
            [0], [0], marker="o", color="w",
            markerfacecolor=HIGHLIGHT_COLOR, markersize=9,
            label="highlighted: " + ", ".join(highlight_forms),
        ))
    if father:
        legend_handles.append(Line2D(
            [0], [0], color=FATHER_COLOR, lw=1.1, ls="--",
            label="father (secondary descriptor)",
        ))

    ax.legend(
        handles=legend_handles, loc="upper center",
        bbox_to_anchor=(0.5, -0.02),
        ncol=3, frameon=False, fontsize=9,
        handletextpad=0.5, columnspacing=1.4,
    )
    # Reserve space below the axes for the legend so tight_layout
    # doesn't squash it back into the plot area.
    fig.subplots_adjust(bottom=0.18)
    return fig


# ──────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────

def main() -> int:
    args = parse_args()

    if not args.pickle.exists():
        sys.exit(
            f"ERROR: SALDO pickle not found at {args.pickle}. Build it via "
            f"`python scripts/build_saldo_graph.py` first."
        )

    g = SaldoGraph.from_pickle(args.pickle)

    focal = pick_sense(g, args.focal, args.sense_index)
    chain = mother_chain(g, focal, max_steps=args.mother_steps)
    sibs = siblings_of(g, focal, args.max_siblings, args.highlight)
    father = g.secondary_descriptor(focal) if args.show_father else None
    show_prim_stub = chain[-1] != "PRIM..1"
    highlight_lower = {w.lower() for w in args.highlight}

    coords, labels = layout_positions(
        g, focal, chain, sibs, father, show_prim_stub, highlight_lower,
    )
    fig = render(
        g, focal, chain, sibs, father, coords, labels,
        show_prim_stub, highlight_lower,
        focal_form=args.focal,
        highlight_forms=args.highlight,
        figsize=tuple(args.figsize),
    )

    # Resolve final output path
    out = args.output
    if out.suffix.lower().lstrip(".") != args.format:
        out = out.with_suffix(f".{args.format}")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight", dpi=300)

    # Diagnostic summary
    print(f"Wrote {out}")
    print(f"  focal sense: {focal} "
          f"(written form '{args.focal}', depth {g.depth(focal)})")
    if len(chain) >= 2:
        print(f"  mother:      {chain[1]} ({short_label(g, chain[1])})")
        for i, anc in enumerate(chain[2:], start=2):
            print(f"  ancestor {i}: {anc} ({short_label(g, anc)})")
    if sibs:
        print(f"  m-siblings ({len(sibs)}): "
              + ", ".join(f"{short_label(g, s)} ({s})" for s in sibs))
    if args.show_father:
        if father:
            print(f"  father:      {father} ({short_label(g, father)})")
        else:
            print("  father:      (focal has no secondary descriptor)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
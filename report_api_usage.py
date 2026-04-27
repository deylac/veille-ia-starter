"""Reporting des appels API LLM enregistrés par observability/api_logger.py.

Usage :
    python report_api_usage.py                # 7 derniers jours, vue par date+modèle
    python report_api_usage.py --days 30      # 30 derniers jours
    python report_api_usage.py --by model     # agrégat sur la période, par modèle uniquement
    python report_api_usage.py --by step      # agrégat par étape du pipeline

Source des données :
    - Supabase table `api_calls` si SUPABASE_URL + SUPABASE_SERVICE_KEY sont définis
    - Fallback : data/api_calls.jsonl
"""
import argparse
import sys
from collections import defaultdict
from typing import Any, Iterable

from observability.api_logger import fetch_recent_calls


def _fmt_int(n: int) -> str:
    """1234 -> '1 234'."""
    return f"{n:,}".replace(",", " ")


def _fmt_tokens(n: int | None) -> str:
    if n is None:
        return "-"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _fmt_cost(c: float) -> str:
    return f"${c:.3f}"


def _print_table(headers: list[str], rows: list[list[str]], aligns: list[str]) -> None:
    """Imprime un tableau aligné en colonnes. aligns[i] in {'l','r'}."""
    if not rows:
        print("(aucun appel sur la période)")
        return

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def _fmt_row(cells: Iterable[str]) -> str:
        out = []
        for i, cell in enumerate(cells):
            if aligns[i] == "r":
                out.append(cell.rjust(widths[i]))
            else:
                out.append(cell.ljust(widths[i]))
        return "  ".join(out)

    print(_fmt_row(headers))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print(_fmt_row(row))


def report_by_date_model(rows: list[dict[str, Any]]) -> None:
    """Vue détaillée : 1 ligne par (date, provider, model)."""
    agg: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(
        lambda: {"calls": 0, "in": 0, "out": 0, "cost": 0.0, "errors": 0}
    )
    for r in rows:
        key = (r.get("date", ""), r.get("provider", ""), r.get("model", ""))
        a = agg[key]
        a["calls"] += 1
        a["in"] += r.get("input_tokens") or 0
        a["out"] += r.get("output_tokens") or 0
        a["cost"] += float(r.get("cost_estimate_usd") or 0)
        if not r.get("success", True):
            a["errors"] += 1

    table_rows = []
    total_cost = 0.0
    total_calls = 0
    for (date, provider, model), a in sorted(agg.items()):
        total_cost += a["cost"]
        total_calls += a["calls"]
        table_rows.append([
            date,
            provider,
            model,
            _fmt_int(a["calls"]),
            _fmt_tokens(a["in"]) if a["in"] else "-",
            _fmt_tokens(a["out"]) if a["out"] else "-",
            _fmt_int(a["errors"]) if a["errors"] else "-",
            _fmt_cost(a["cost"]),
        ])

    _print_table(
        headers=["Date", "Provider", "Model", "Appels", "Tok in", "Tok out", "Err", "Coût USD"],
        rows=table_rows,
        aligns=["l", "l", "l", "r", "r", "r", "r", "r"],
    )
    print()
    print(f"TOTAL : {_fmt_int(total_calls)} appels, coût estimé {_fmt_cost(total_cost)}")


def report_by_model(rows: list[dict[str, Any]]) -> None:
    """Vue agrégée sur la période : 1 ligne par modèle."""
    agg: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"calls": 0, "in": 0, "out": 0, "cost": 0.0, "errors": 0, "provider": ""}
    )
    for r in rows:
        model = r.get("model", "")
        a = agg[model]
        a["provider"] = r.get("provider", "")
        a["calls"] += 1
        a["in"] += r.get("input_tokens") or 0
        a["out"] += r.get("output_tokens") or 0
        a["cost"] += float(r.get("cost_estimate_usd") or 0)
        if not r.get("success", True):
            a["errors"] += 1

    table_rows = []
    total_cost = 0.0
    total_calls = 0
    for model, a in sorted(agg.items(), key=lambda kv: -kv[1]["cost"]):
        total_cost += a["cost"]
        total_calls += a["calls"]
        table_rows.append([
            a["provider"],
            model,
            _fmt_int(a["calls"]),
            _fmt_tokens(a["in"]) if a["in"] else "-",
            _fmt_tokens(a["out"]) if a["out"] else "-",
            _fmt_int(a["errors"]) if a["errors"] else "-",
            _fmt_cost(a["cost"]),
        ])

    _print_table(
        headers=["Provider", "Model", "Appels", "Tok in", "Tok out", "Err", "Coût USD"],
        rows=table_rows,
        aligns=["l", "l", "r", "r", "r", "r", "r"],
    )
    print()
    print(f"TOTAL période : {_fmt_int(total_calls)} appels, coût estimé {_fmt_cost(total_cost)}")


def report_by_step(rows: list[dict[str, Any]]) -> None:
    """Vue agrégée par étape du pipeline (context.step)."""
    agg: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"calls": 0, "cost": 0.0, "errors": 0}
    )
    for r in rows:
        ctx = r.get("context") or {}
        step = ctx.get("step", "(unknown)") if isinstance(ctx, dict) else "(unknown)"
        a = agg[step]
        a["calls"] += 1
        a["cost"] += float(r.get("cost_estimate_usd") or 0)
        if not r.get("success", True):
            a["errors"] += 1

    table_rows = []
    total_cost = 0.0
    total_calls = 0
    for step, a in sorted(agg.items(), key=lambda kv: -kv[1]["cost"]):
        total_cost += a["cost"]
        total_calls += a["calls"]
        table_rows.append([
            step,
            _fmt_int(a["calls"]),
            _fmt_int(a["errors"]) if a["errors"] else "-",
            _fmt_cost(a["cost"]),
        ])

    _print_table(
        headers=["Étape pipeline", "Appels", "Err", "Coût USD"],
        rows=table_rows,
        aligns=["l", "r", "r", "r"],
    )
    print()
    print(f"TOTAL période : {_fmt_int(total_calls)} appels, coût estimé {_fmt_cost(total_cost)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=int, default=7, help="Fenêtre en jours (défaut: 7)")
    parser.add_argument(
        "--by",
        choices=["date", "model", "step"],
        default="date",
        help="Pivot d'agrégation : 'date' (défaut, par date+modèle), 'model' (par modèle), 'step' (par étape pipeline)",
    )
    args = parser.parse_args()

    rows = fetch_recent_calls(days=args.days)
    print(f"Appels API sur les {args.days} derniers jours : {len(rows)} entrées\n")

    if args.by == "date":
        report_by_date_model(rows)
    elif args.by == "model":
        report_by_model(rows)
    elif args.by == "step":
        report_by_step(rows)

    return 0


if __name__ == "__main__":
    sys.exit(main())

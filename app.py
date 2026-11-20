"""EcoCode - a small Flask prototype for code performance and sustainability reports.

Important: submitted code is treated as text only. It is never compiled, interpreted
or executed. Every measurement shown in the interface is illustrative demonstration
data produced by the simple model in this file.
"""

import csv
import io
import math
import re
from datetime import date

from flask import Flask, Response, flash, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["SECRET_KEY"] = "ecocode-prototype-key-not-for-production"
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024  # 1 MB upload limit

MAX_CODE_CHARS = 3000  # keeps the demonstration session cookie small
GRID_G_PER_WH = 400    # fixed illustrative grid carbon factor

SAMPLE_CODE = """def find_duplicates(items):
    duplicates = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i] == items[j] and items[i] not in duplicates:
                duplicates.append(items[i])
    return duplicates


def total_cost(orders):
    total = 0
    for order in orders:
        total = total + order["price"] * order["qty"]
    return total
"""

OPTIMIZED_CODE = """def find_duplicates(items):
    ordered = sorted(items)
    duplicates = []
    for prev, cur in zip(ordered, ordered[1:]):
        if prev == cur and (not duplicates or duplicates[-1] != cur):
            duplicates.append(cur)
    return duplicates


def total_cost(orders):
    return sum(o["price"] * o["qty"] for o in orders)
"""

CHANGED_OPTIMIZED_LINES = (2, 4, 5, 11)

HISTORY = [
    {"id": 1, "name": "find_duplicates.py", "language": "Python", "complexity": "O(n²)", "ms": 125, "date": "2026-11-19", "n": 1000},
    {"id": 2, "name": "matrix_multiply.py", "language": "Python", "complexity": "O(n³)", "ms": 890, "date": "2026-11-18", "n": 200},
    {"id": 3, "name": "binary_search.py", "language": "Python", "complexity": "O(log n)", "ms": 0.4, "date": "2026-11-17", "n": 100000},
    {"id": 4, "name": "merge_sort.py", "language": "Python", "complexity": "O(n log n)", "ms": 42, "date": "2026-11-15", "n": 1000},
    {"id": 5, "name": "word_count.py", "language": "Python", "complexity": "O(n)", "ms": 18, "date": "2026-11-12", "n": 5000},
    {"id": 6, "name": "fib_recursive.py", "language": "Python", "complexity": "O(2ⁿ)", "ms": 5400, "date": "2026-11-09", "n": 30},
    {"id": 7, "name": "cache_layer.py", "language": "Python", "complexity": "O(n)", "ms": 9, "date": "2026-11-05", "n": 2000},
    {"id": 8, "name": "graph_bfs.py", "language": "Python", "complexity": "O(n + m)", "ms": 31, "date": "2026-11-02", "n": 3000},
]

FINDINGS = {
    "loops": [
        {"line": "03", "text": "for i in range(len(items))", "depth": 1, "cost": "O(n)"},
        {"line": "04", "text": "for j in range(i + 1, len(items))", "depth": 2, "cost": "O(n²) total"},
        {"line": "12", "text": "for order in orders", "depth": 1, "cost": "O(n)"},
    ],
    "inefficient": [
        "Membership test on a list scans the collection again at line 05.",
        "Manual accumulation at line 13 can be replaced by sum() over a generator.",
    ],
    "explanation": (
        "Two nested loops compare every pair of items, so the work grows with the "
        "square of N. Doubling the input size roughly quadruples the runtime and the "
        "energy required for one run."
    ),
    "bottlenecks": [
        "Pairwise comparison in find_duplicates is the dominant cost in this example.",
        "The membership test inside the inner loop adds repeated linear scans.",
    ],
    "recommendations": [
        "Sort once, then compare adjacent items to reach O(n log n).",
        "Replace manual accumulation with sum() and a generator expression.",
        "Use a set when items are hashable and only uniqueness matters.",
    ],
    "notes": [
        "Replaced the O(n²) nested loops with sort + adjacent comparison, O(n log n).",
        "Removed the repeated list scan by checking only the last recorded duplicate.",
        "Replaced manual accumulation with sum() over a generator expression.",
    ],
}

OTHER_EXPLANATIONS = {
    "O(n³)": "Three nested passes make the work grow with the cube of N. Small increases in input size have a large effect.",
    "O(log n)": "The search space is divided on each step, so the work grows very slowly as N increases.",
    "O(n log n)": "The input is divided and merged, giving a much gentler curve than quadratic approaches.",
    "O(n)": "Each item is visited a constant number of times, so the work grows linearly with N.",
    "O(2ⁿ)": "Recursive branching doubles the work with each additional item. This is the least scalable pattern shown here.",
    "O(n + m)": "Vertices and edges are each visited once, so the cost depends on both dimensions of the graph.",
}


# ---------------------------------------------------------------------------
# Demonstration model. These are illustrative figures, not measurements.
# ---------------------------------------------------------------------------
def num(value):
    """Compact human-readable number for demonstration values."""
    if value >= 1000:
        return f"{value:,.0f}"
    if value >= 100:
        return f"{value:.0f}"
    if value >= 1:
        return f"{value:.2f}".rstrip("0").rstrip(".")
    if value >= 0.01:
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return f"{value:.3g}"


def fmt_time(ms):
    if ms < 1000:
        return num(ms), "ms"
    if ms < 60000:
        return num(ms / 1000), "s"
    return num(ms / 60000), "min"


def fmt_energy(wh):
    return num(wh), "Wh"


def fmt_co2(grams):
    if grams < 1000:
        return num(grams), "g CO₂e"
    return num(grams / 1000), "kg CO₂e"


def join(value, unit):
    return f"{value} {unit}"


def demo_point(n, variant):
    if variant == "orig":
        ms = 125 * (n / 1000) ** 2
        wh = ms * 1.6e-5
    else:
        ms = 42 * (n * math.log2(max(n, 2))) / (1000 * math.log2(1000))
        wh = ms * 1.905e-5
    return {"time_ms": ms, "energy_wh": wh, "co2_g": wh * GRID_G_PER_WH}


def bar_height(value, maximum):
    """Log-scaled bar length: the largest input is 100%, four decades down is 0%."""
    if value <= 0 or maximum <= 0:
        return 2
    scaled = 100 + (math.log10(value / maximum) / 4) * 100
    return max(2, min(100, round(scaled, 1)))


def format_metrics(point, complexity):
    t_value, t_unit = fmt_time(point["time_ms"])
    e_value, e_unit = fmt_energy(point["energy_wh"])
    c_value, c_unit = fmt_co2(point["co2_g"])
    return {
        "complexity": complexity,
        "time": t_value,
        "time_unit": t_unit,
        "energy": e_value,
        "energy_unit": e_unit,
        "co2": c_value,
        "co2_unit": c_unit,
    }


def build_charts(n):
    sizes = [max(10, int(round(n * factor))) for factor in (0.1, 0.25, 0.5, 1, 2, 4)]
    raw = [(size, demo_point(size, "orig"), demo_point(size, "opt")) for size in sizes]
    maxima = {
        key: max(original[key] for _, original, _ in raw)
        for key in ("time_ms", "energy_wh", "co2_g")
    }

    points = []
    for size, original, optimized in raw:
        t_o, t_u = fmt_time(original["time_ms"])
        e_o, e_u = fmt_energy(original["energy_wh"])
        c_o, c_u = fmt_co2(original["co2_g"])
        points.append({
            "label": f"{size:,}",
            "time_o": bar_height(original["time_ms"], maxima["time_ms"]),
            "time_p": bar_height(optimized["time_ms"], maxima["time_ms"]),
            "energy_o": bar_height(original["energy_wh"], maxima["energy_wh"]),
            "energy_p": bar_height(optimized["energy_wh"], maxima["energy_wh"]),
            "co2_o": bar_height(original["co2_g"], maxima["co2_g"]),
            "co2_p": bar_height(optimized["co2_g"], maxima["co2_g"]),
            "time_value": join(t_o, t_u),
            "energy_value": join(e_o, e_u),
            "co2_value": join(c_o, c_u),
        })

    max_n = sizes[-1]
    operations = [
        ("O(log n)", math.log2(max_n), "Divide and conquer"),
        ("O(n)", max_n, "One pass"),
        ("O(n log n)", max_n * math.log2(max_n), "Sort and merge"),
        ("O(n²)", max_n ** 2, "Every pair"),
    ]
    max_ops = max(value for _, value, _ in operations)
    scalability = [
        {
            "label": label,
            "width": round((math.log10(value) + 1) / (math.log10(max_ops) + 1) * 100, 1),
            "note": note,
            "active": label == "O(n²)",
            "optimized": label == "O(n log n)",
        }
        for label, value, note in operations
    ]
    return {"points": points, "scalability": scalability, "max_label": f"{max_n:,}"}


def build_findings(complexity):
    findings = dict(FINDINGS)
    if complexity in OTHER_EXPLANATIONS:
        findings["explanation"] = OTHER_EXPLANATIONS[complexity]
        findings["generic"] = True
    else:
        findings["generic"] = False
    return findings


def build_analysis(name, language, n, code, complexity="O(n²)"):
    code = code[:MAX_CODE_CHARS]
    original = demo_point(n, "orig")
    optimized = demo_point(n, "opt")
    return {
        "meta": {
            "name": name,
            "language": language,
            "n": n,
            "lines": len(code.splitlines()),
            "date": date.today().isoformat(),
        },
        "code": code,
        "metrics": format_metrics(original, complexity),
        "optimized": format_metrics(optimized, "O(n log n)"),
        "raw": {"orig": original, "opt": optimized},
        "improvements": {
            "time": round((1 - optimized["time_ms"] / original["time_ms"]) * 100),
            "energy": round((1 - optimized["energy_wh"] / original["energy_wh"]) * 100),
            "co2": round((1 - optimized["co2_g"] / original["co2_g"]) * 100),
        },
        "charts": build_charts(n),
        "findings": build_findings(complexity),
    }


def get_analysis():
    analysis = session.get("analysis")
    if not analysis:
        analysis = build_analysis("find_duplicates.py", "Python", 1000, SAMPLE_CODE)
        session["analysis"] = analysis
    return analysis


def code_lines(code, highlights=()):
    return [
        {"num": index + 1, "text": line or " ", "hot": index + 1 in highlights}
        for index, line in enumerate(code.splitlines())
    ]


def filtered_history():
    query = request.args.get("q", "").strip().lower()
    language = request.args.get("language", "")
    complexity = request.args.get("complexity", "")
    rows = []
    for row in HISTORY:
        if query and query not in row["name"].lower():
            continue
        if language and language != row["language"]:
            continue
        if complexity and complexity != row["complexity"]:
            continue
        item = dict(row)
        item["time_display"] = join(*fmt_time(row["ms"]))
        energy = row["ms"] * 1.6e-5
        item["energy_display"] = join(*fmt_energy(energy))
        item["co2_value"] = energy * GRID_G_PER_WH
        item["co2_display"] = join(*fmt_co2(item["co2_value"]))
        rows.append(item)
    return rows


def history_summary(rows):
    if not rows:
        return {"count": 0, "average_time": "—", "total_co2": "—"}
    average_ms = sum(row["ms"] for row in rows) / len(rows)
    total_co2 = sum(row["co2_value"] for row in rows)
    return {
        "count": len(rows),
        "average_time": join(*fmt_time(average_ms)),
        "total_co2": join(*fmt_co2(total_co2)),
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["GET", "POST"])
def analyze():
    code = SAMPLE_CODE
    name = "find_duplicates.py"
    language = "Python"
    n = 1000
    errors = []
    notice = None

    if request.method == "POST":
        action = request.form.get("action", "analyze")
        code = request.form.get("code", "")
        name = secure_filename(request.form.get("name", "").strip()) or "untitled.py"
        language = request.form.get("language", "Python")

        if "preset_n" in request.form:
            n = int(request.form["preset_n"])
            action = "preset"
        else:
            try:
                n = int(request.form.get("n", "1000"))
            except (TypeError, ValueError):
                errors.append("Enter a whole number for the input size.")

        uploaded = request.files.get("source_file")
        if uploaded and uploaded.filename:
            filename = secure_filename(uploaded.filename)
            if not filename.lower().endswith((".py", ".txt")):
                errors.append("Upload a .py or .txt source file.")
            else:
                text = uploaded.read().decode("utf-8", errors="replace")
                if len(text) > MAX_CODE_CHARS:
                    text = text[:MAX_CODE_CHARS]
                    notice = f"Uploaded file truncated to {MAX_CODE_CHARS:,} characters for this prototype."
                code = text
                name = filename

        if action == "clear":
            code = ""
            notice = "Editor cleared."
        elif action == "sample":
            code = SAMPLE_CODE
            name = "find_duplicates.py"
            n = 1000
            notice = "Sample program restored."
        elif action == "analyze":
            if not code.strip():
                errors.append("Add some source code before analyzing.")
            if len(code) > MAX_CODE_CHARS:
                errors.append(f"Keep the program under {MAX_CODE_CHARS:,} characters for this prototype.")
            if not 10 <= n <= 1_000_000:
                errors.append("Input size must be between 10 and 1,000,000.")
            if not errors:
                session["analysis"] = build_analysis(name, language, n, code)
                return redirect(url_for("dashboard"))

    return render_template(
        "workspace.html",
        code=code,
        name=name,
        language=language,
        n=n,
        errors=errors,
        notice=notice,
        max_chars=MAX_CODE_CHARS,
    )


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", a=get_analysis())


@app.route("/comparison")
def comparison():
    analysis = get_analysis()
    return render_template(
        "comparison.html",
        a=analysis,
        original_lines=code_lines(analysis["code"]),
        optimized_lines=code_lines(OPTIMIZED_CODE, CHANGED_OPTIMIZED_LINES),
    )


@app.route("/download-optimized")
def download_optimized():
    analysis = get_analysis()
    base = re.sub(r"\.[^.]+$", "", analysis["meta"]["name"]) or "program"
    filename = secure_filename(base + "_optimized.py")
    return Response(
        OPTIMIZED_CODE,
        mimetype="text/x-python",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.route("/history")
def history():
    rows = filtered_history()
    return render_template(
        "history.html", view="history", rows=rows, summary=history_summary(rows), filters=request.args
    )


@app.route("/reports")
def reports():
    rows = filtered_history()
    return render_template(
        "history.html", view="reports", rows=rows, summary=history_summary(rows), filters=request.args
    )


@app.route("/history/view", methods=["POST"])
def history_view():
    row = next((item for item in HISTORY if str(item["id"]) == request.form.get("id", "")), None)
    if row:
        session["analysis"] = build_analysis(
            row["name"], row["language"], row["n"], SAMPLE_CODE, row["complexity"]
        )
    return redirect(url_for("dashboard"))


@app.route("/history/export.csv")
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["project", "language", "complexity", "execution_time_ms", "input_size", "analysis_date"])
    for row in filtered_history():
        writer.writerow([row["name"], row["language"], row["complexity"], row["ms"], row["n"], row["date"]])
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": 'attachment; filename="ecocode-history.csv"'},
    )


@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        flash("Preferences recorded for this prototype. They do not affect the demonstration model.", "ok")
        return redirect(url_for("settings"))
    return render_template("settings.html")


if __name__ == "__main__":
    app.run(debug=True)

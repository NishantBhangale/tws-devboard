
import os
import html
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

TOKEN = os.environ["SONAR_TOKEN"]
PROJECT = os.environ["SONAR_PROJECT_KEY"]

BASE_URL = "https://sonarcloud.io"
OUTPUT = "reports/sonarcloud-report.html"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json"
}


def api_get(endpoint, params=None):
    query = urllib.parse.urlencode(params or {})
    url = f"{BASE_URL}{endpoint}?{query}"

    request = urllib.request.Request(
        url,
        headers=HEADERS
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode())


def get_measures():
    metrics = ",".join([
        "bugs",
        "vulnerabilities",
        "code_smells",
        "coverage",
        "duplicated_lines_density",
        "ncloc",
        "reliability_rating",
        "security_rating",
        "sqale_rating"
    ])

    data = api_get(
        "/api/measures/component",
        {
            "component": PROJECT,
            "metricKeys": metrics
        }
    )

    return {
        item["metric"]: item.get("value", "N/A")
        for item in data["component"].get("measures", [])
    }


def get_quality_gate():
    data = api_get(
        "/api/qualitygates/project_status",
        {"projectKey": PROJECT}
    )

    return data["projectStatus"]


def get_issues():
    issues = []
    page = 1

    while True:
        data = api_get(
            "/api/issues/search",
            {
                "componentKeys": PROJECT,
                "resolved": "false",
                "ps": 500,
                "p": page
            }
        )

        batch = data.get("issues", [])
        issues.extend(batch)

        total = data.get("total", 0)

        if not batch or len(issues) >= total:
            break

        page += 1

    return issues


def safe(value):
    return html.escape(str(value or "N/A"))


def create_html(measures, gate, issues):
    gate_status = gate.get("status", "UNKNOWN")

    gate_conditions = gate.get("conditions", [])

    cards = [
        ("Bugs", measures.get("bugs", "N/A")),
        ("Vulnerabilities", measures.get("vulnerabilities", "N/A")),
        ("Code Smells", measures.get("code_smells", "N/A")),
        ("Coverage", measures.get("coverage", "N/A") + "%"),
        ("Duplications", measures.get("duplicated_lines_density", "N/A") + "%"),
        ("Lines of Code", measures.get("ncloc", "N/A")),
        ("Reliability Rating", measures.get("reliability_rating", "N/A")),
        ("Security Rating", measures.get("security_rating", "N/A")),
        ("Maintainability Rating", measures.get("sqale_rating", "N/A"))
    ]

    card_html = "".join(
        f"""
        <div class="card">
          <div class="card-label">{safe(name)}</div>
          <div class="card-value">{safe(value)}</div>
        </div>
        """
        for name, value in cards
    )

    issue_rows = ""

    for issue in issues:
        component = issue.get("component", "")
        file_name = component.split(":", 1)[-1]
        line = issue.get("line", "-")

        issue_rows += f"""
        <tr>
          <td>{safe(issue.get("severity"))}</td>
          <td>{safe(issue.get("type"))}</td>
          <td>{safe(issue.get("rule"))}</td>
          <td>{safe(file_name)}:{safe(line)}</td>
          <td>{safe(issue.get("message"))}</td>
        </tr>
        """

    if not issue_rows:
        issue_rows = """
        <tr><td colspan="5">No open issues returned by SonarCloud.</td></tr>
        """

    condition_rows = ""

    for condition in gate_conditions:
        condition_rows += f"""
        <tr>
          <td>{safe(condition.get("metricKey"))}</td>
          <td>{safe(condition.get("comparator"))}</td>
          <td>{safe(condition.get("errorThreshold"))}</td>
          <td>{safe(condition.get("actualValue"))}</td>
          <td>{safe(condition.get("status"))}</td>
        </tr>
        """

    gate_class = (
        "passed" if gate_status == "OK" else "failed"
    )

    branch = os.getenv("GITHUB_BRANCH", "unknown")
    commit = os.getenv("GITHUB_SHA", "unknown")
    repository = os.getenv("GITHUB_REPOSITORY", "unknown")
    run_number = os.getenv("GITHUB_RUN_NUMBER", "unknown")

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )

    dashboard = (
        f"{BASE_URL}/dashboard?id="
        f"{urllib.parse.quote(PROJECT, safe='')}"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DevBoard - SonarCloud Report</title>

<style>
* {{ box-sizing: border-box; }}

body {{
    margin: 0;
    padding: 30px;
    background: #f1f5f9;
    color: #1e293b;
    font-family: Arial, sans-serif;
}}

.container {{
    max-width: 1200px;
    margin: auto;
}}

header {{
    background: #0f172a;
    color: white;
    padding: 28px;
    border-radius: 12px;
}}

header h1 {{ margin: 0 0 10px; }}

.meta {{
    color: #cbd5e1;
    line-height: 1.8;
    font-size: 13px;
}}

.gate {{
    margin: 22px 0;
    padding: 18px;
    border-radius: 10px;
    font-weight: bold;
}}

.passed {{ background: #dcfce7; color: #166534; }}
.failed {{ background: #fee2e2; color: #991b1b; }}

.grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 15px;
}}

.card, .section {{
    background: white;
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,.04);
}}

.card-label {{
    color: #64748b;
    font-size: 13px;
}}

.card-value {{
    font-size: 28px;
    font-weight: bold;
    margin-top: 12px;
}}

.section {{ margin-top: 24px; }}

table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}}

th, td {{
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #e2e8f0;
    overflow-wrap: anywhere;
}}

th {{ background: #f8fafc; }}

.table-wrap {{ overflow-x: auto; }}

a {{ color: #2563eb; text-decoration: none; }}

footer {{
    margin-top: 25px;
    color: #64748b;
    font-size: 12px;
}}

@media print {{
    body {{ background: white; padding: 10px; }}
    .card, .section {{ box-shadow: none; }}
}}
</style>
</head>

<body>
<div class="container">

<header>
    <h1>DevBoard - SonarCloud Analysis</h1>
    <div class="meta">
        Repository: {safe(repository)}<br>
        Project: {safe(PROJECT)}<br>
        Branch: {safe(branch)}<br>
        Commit: {safe(commit)}<br>
        Workflow Run: {safe(run_number)}<br>
        Generated: {safe(timestamp)}
    </div>
    <p><a href="{safe(dashboard)}">Open SonarCloud Dashboard ↗</a></p>
</header>

<div class="gate {gate_class}">
    Quality Gate: {safe(gate_status)}
</div>

<h2>Project Metrics</h2>

<div class="grid">
    {card_html}
</div>

<div class="section">
<h2>Quality Gate Conditions</h2>
<div class="table-wrap">
<table>
<thead>
<tr>
<th>Metric</th>
<th>Comparator</th>
<th>Threshold</th>
<th>Actual</th>
<th>Status</th>
</tr>
</thead>
<tbody>
{condition_rows or '<tr><td colspan="5">No conditions returned.</td></tr>'}
</tbody>
</table>
</div>
</div>

<div class="section">
<h2>Open Code Issues ({len(issues)})</h2>
<div class="table-wrap">
<table>
<thead>
<tr>
<th>Severity</th>
<th>Type</th>
<th>Rule</th>
<th>File / Line</th>
<th>Description</th>
</tr>
</thead>
<tbody>
{issue_rows}
</tbody>
</table>
</div>
</div>

<footer>
Generated from SonarCloud Web API.
This report represents the data available when it was generated.
</footer>

</div>
</body>
</html>"""


def main():
    print("Fetching SonarCloud project metrics...")
    measures = get_measures()

    print("Fetching Quality Gate...")
    gate = get_quality_gate()

    print("Fetching open issues...")
    issues = get_issues()

    report = create_html(measures, gate, issues)

    os.makedirs("reports", exist_ok=True)

    with open(OUTPUT, "w", encoding="utf-8") as file:
        file.write(report)

    print(f"HTML report generated: {OUTPUT}")
    print(f"Quality Gate: {gate.get('status')}")
    print(f"Open issues: {len(issues)}")


if __name__ == "__main__":
    main()

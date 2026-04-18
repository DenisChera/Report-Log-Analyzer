import httpx
import json

# Test health
resp = httpx.get("http://localhost:8000/health")
print("Health:", resp.json())

# Test /parse with a FAIL report
with open(r"d:\Report-Log-Analyzer\RESULTS\html_report_3182026_at_154830.html", "rb") as f:
    resp = httpx.post("http://localhost:8000/parse", files={"file": ("report.html", f, "text/html")})
data = resp.json()
tc = data["test_cases"][0]
print(f"Parse FAIL: {data['total_tests']} tests, {data['passed']} passed, {data['failed']} failed")
print(f"  Test: {tc['test_name']} -> {tc['result']}")
print(f"  Error: {tc['error_message'][:120]}...")

# Test /parse with a PASS report
with open(r"d:\Report-Log-Analyzer\RESULTS\html_report_3132026_at_114322.html", "rb") as f:
    resp2 = httpx.post("http://localhost:8000/parse", files={"file": ("pass_report.html", f, "text/html")})
data2 = resp2.json()
tc2 = data2["test_cases"][0]
print(f"Parse PASS: {tc2['test_name']} -> {tc2['result']}")

# Test unsupported format
resp3 = httpx.post("http://localhost:8000/parse", files={"file": ("report.pdf", b"fake pdf", "application/pdf")})
print(f"Unsupported: {resp3.status_code} - {resp3.json()['detail'][:80]}")

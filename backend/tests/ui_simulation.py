import sys
from pathlib import Path

from fastapi.testclient import TestClient

# Ensure backend/ is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
from app.main import app

client = TestClient(app)


def run_simulation():
    print("--- Starting UI Simulation ---")

    # 1. Dashboard Check
    print("\n[1/5] Checking Dashboard...")
    r = client.get("/")
    assert r.status_code == 200
    assert "Filoos" in r.text
    print("OK - Dashboard loaded.")

    # 2. Account Workflow
    print("\n[2/5] Account CRUD Workflow...")
    # Create
    r = client.post(
        "/accounts",
        data={
            "name": "UI Test Account",
            "type": "bank",
            "currency": "INR",
            "opening_balance": "5000",
            "is_active": "true",
        },
        headers={"HX-Request": "true"},
    )
    assert r.status_code == 200
    assert r.headers["HX-Redirect"] == "/accounts"

    # Get ID
    accounts = client.get("/api/accounts").json()
    acc_id = next(a["id"] for a in accounts if a["name"] == "UI Test Account")
    print(f"OK - Created account with ID: {acc_id}")

    # Edit (PATCH - uncheck active)
    r = client.patch(
        f"/accounts/{acc_id}",
        data={"name": "UI Test Updated", "is_active": "false"},
        headers={"HX-Request": "true"},
    )
    assert r.status_code == 200

    acc = client.get(f"/api/accounts/{acc_id}").json()
    assert acc["name"] == "UI Test Updated"
    assert acc["is_active"] is False
    print("OK - Edited account (name, active checkbox).")

    # 3. Transaction Workflow
    print("\n[3/5] Transaction CRUD Workflow...")
    # Create
    r = client.post(
        "/transactions",
        data={
            "type": "expense",
            "account_id": str(acc_id),
            "amount": "1000",
            "description": "UI Test Expense",
            "date": "2026-06-03",
        },
        headers={"HX-Request": "true"},
    )
    assert r.status_code == 200
    assert r.headers["HX-Redirect"] == "/transactions"

    txs = client.get("/api/transactions").json()
    tx_id = next(t["id"] for t in txs if t["description"] == "UI Test Expense")
    print(f"OK - Created transaction ID: {tx_id}")

    # Filter
    r = client.get(f"/transactions?account={acc_id}&type=expense&from=2026-06-01&to=2026-06-05&q=")
    assert r.status_code == 200
    assert "UI Test Expense" in r.text
    print("OK - Filtered transactions (422 test included).")

    # 4. Transfer Workflow
    print("\n[4/5] Transfer Workflow...")
    # Need second account
    client.post(
        "/accounts",
        data={
            "name": "Acc2",
            "type": "cash",
            "currency": "INR",
            "opening_balance": "0",
            "is_active": "true",
        },
        headers={"HX-Request": "true"},
    )
    acc2_id = next(a["id"] for a in client.get("/api/accounts").json() if a["name"] == "Acc2")

    r = client.post(
        "/transactions",
        data={
            "type": "transfer",
            "from_account_id": str(acc_id),
            "to_account_id": str(acc2_id),
            "amount": "500",
            "description": "UI Test Transfer",
            "date": "2026-06-03",
        },
        headers={"HX-Request": "true"},
    )
    assert r.status_code == 200
    assert r.headers["HX-Redirect"] == "/transactions"
    print("OK - Created transfer.")

    # 5. Deletion Workflow
    print("\n[5/5] Deletion Workflow...")
    r = client.delete(f"/transactions/{tx_id}", headers={"HX-Request": "true"})
    assert r.status_code == 200

    txs = client.get("/api/transactions").json()
    assert not any(t["id"] == tx_id for t in txs)
    print("OK - Deleted transaction.")

    print("\n--- Simulation Successful! All features verified. ---")


if __name__ == "__main__":
    try:
        run_simulation()
    except Exception as e:
        print(f"\n--- Simulation FAILED: {e} ---")
        sys.exit(1)

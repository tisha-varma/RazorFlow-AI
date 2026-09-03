import pytest


class TestCartEndpoints:
    def test_create_cart(self, client, seed_data):
        resp = client.post("/api/cart", json={"session_id": "test-sess", "merchant_id": 1})
        assert resp.status_code == 201
        data = resp.json()
        assert data["session_id"] == "test-sess"
        assert data["status"] == "active"

    def test_get_cart(self, client, seed_data):
        create = client.post("/api/cart", json={"session_id": "test-sess", "merchant_id": 1})
        cart_id = create.json()["id"]
        resp = client.get(f"/api/cart/{cart_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == cart_id

    def test_add_item(self, client, seed_data):
        p1 = seed_data["p1"]
        cart = client.post("/api/cart", json={"session_id": "test-sess", "merchant_id": 1}).json()
        resp = client.post(f"/api/cart/{cart['id']}/items", json={
            "product_id": p1.id,
            "quantity": 1
        })
        assert resp.status_code == 201
        items = resp.json()["items"]
        assert len(items) == 1

    def test_add_item_with_variant(self, client, seed_data):
        p1 = seed_data["p1"]
        cart = client.post("/api/cart", json={"session_id": "test-sess", "merchant_id": 1}).json()
        resp = client.post(f"/api/cart/{cart['id']}/items", json={
            "product_id": p1.id,
            "variant_id": None,
            "quantity": 1
        })
        assert resp.status_code == 201

    def test_add_duplicate_item_increments(self, client, seed_data):
        p1 = seed_data["p1"]
        cart = client.post("/api/cart", json={"session_id": "test-sess", "merchant_id": 1}).json()
        client.post(f"/api/cart/{cart['id']}/items", json={"product_id": p1.id, "quantity": 1})
        resp = client.post(f"/api/cart/{cart['id']}/items", json={"product_id": p1.id, "quantity": 2})
        items = resp.json()["items"]
        assert items[0]["quantity"] == 3

    def test_update_quantity(self, client, seed_data):
        p1 = seed_data["p1"]
        cart = client.post("/api/cart", json={"session_id": "test-sess", "merchant_id": 1}).json()
        add_resp = client.post(f"/api/cart/{cart['id']}/items", json={"product_id": p1.id, "quantity": 1})
        item_id = add_resp.json()["items"][0]["id"]
        resp = client.put(f"/api/cart/{cart['id']}/items/{item_id}", json={"quantity": 5})
        assert resp.status_code == 200
        assert resp.json()["items"][0]["quantity"] == 5

    def test_remove_item(self, client, seed_data):
        p1 = seed_data["p1"]
        cart = client.post("/api/cart", json={"session_id": "test-sess", "merchant_id": 1}).json()
        add_resp = client.post(f"/api/cart/{cart['id']}/items", json={"product_id": p1.id, "quantity": 1})
        item_id = add_resp.json()["items"][0]["id"]
        resp = client.delete(f"/api/cart/{cart['id']}/items/{item_id}")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 0

    def test_calculate_totals(self, client, seed_data):
        p1 = seed_data["p1"]
        cart = client.post("/api/cart", json={"session_id": "test-sess", "merchant_id": 1}).json()
        client.post(f"/api/cart/{cart['id']}/items", json={"product_id": p1.id, "quantity": 2})
        resp = client.get(f"/api/cart/{cart['id']}/calculate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["subtotal_paise"] == 449900 * 2
        assert data["item_count"] == 1

    def test_cart_not_found(self, client):
        resp = client.get("/api/cart/9999")
        assert resp.status_code == 404

    def test_related_second_item_inferred_upsell(self, client, seed_data):
        # p3 (socks) complements p1 (explicit relation) -> upsell even unflagged.
        p1 = seed_data["p1"]
        p3 = seed_data["p3"]
        cart = client.post("/api/cart", json={"session_id": "upsell-inf", "merchant_id": 1}).json()
        client.post(f"/api/cart/{cart['id']}/items", json={"product_id": p1.id, "quantity": 1})
        resp = client.post(f"/api/cart/{cart['id']}/items", json={"product_id": p3.id, "quantity": 1})
        items = {i["product_name"]: i for i in resp.json()["items"]}
        assert items["RunPro Sprint"]["is_upsell"] is False
        assert items["Running Socks"]["is_upsell"] is True

    def test_unrelated_second_item_not_upsell(self, client, seed_data, db_session):
        from backend.models import Product
        merchant_id = seed_data["merchant"].id
        lone = Product(
            merchant_id=merchant_id, name="Lone Cap", description="d",
            category="Accessories", base_price_paise=10000,
            tags=["unrelated999"], is_active=True
        )
        db_session.add(lone)
        db_session.commit()

        p1 = seed_data["p1"]
        cart = client.post("/api/cart", json={"session_id": "upsell-neg", "merchant_id": 1}).json()
        client.post(f"/api/cart/{cart['id']}/items", json={"product_id": p1.id, "quantity": 1})
        resp = client.post(f"/api/cart/{cart['id']}/items", json={"product_id": lone.id, "quantity": 1})
        items = {i["product_name"]: i for i in resp.json()["items"]}
        assert items["Lone Cap"]["is_upsell"] is False

    def test_add_item_returns_policy_allowed(self, client, seed_data):
        p1 = seed_data["p1"]
        cart = client.post("/api/cart", json={"session_id": "test-sess", "merchant_id": 1}).json()
        resp = client.post(f"/api/cart/{cart['id']}/items", json={
            "product_id": p1.id,
            "quantity": 1
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["policy_allowed"] is True

    def test_add_item_returns_policy_blocked(self, client, seed_data):
        p1 = seed_data["p1"]
        cart = client.post("/api/cart", json={"session_id": "test-sess", "merchant_id": 1}).json()
        resp = client.post(f"/api/cart/{cart['id']}/items", json={
            "product_id": p1.id,
            "quantity": 2
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["policy_allowed"] is False
        assert "exceeds" in data["policy_reason"].lower()

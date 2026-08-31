import pytest


class TestCatalogEndpoints:
    def test_list_products(self, client, seed_data):
        resp = client.get("/api/catalog/products")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 3
        assert len(data["products"]) >= 3

    def test_search_products(self, client, seed_data):
        resp = client.get("/api/catalog/products?query=running")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2

    def test_filter_by_category(self, client, seed_data):
        resp = client.get("/api/catalog/products?category=Accessories")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_filter_by_price(self, client, seed_data):
        resp = client.get("/api/catalog/products?max_price=100000")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_get_product(self, client, seed_data):
        p1 = seed_data["p1"]
        resp = client.get(f"/api/catalog/products/{p1.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "RunPro Sprint"

    def test_get_product_not_found(self, client):
        resp = client.get("/api/catalog/products/9999")
        assert resp.status_code == 404

    def test_get_categories(self, client, seed_data):
        resp = client.get("/api/catalog/categories")
        assert resp.status_code == 200
        cats = resp.json()
        assert "Running Shoes" in cats
        assert "Trail Shoes" in cats
        assert "Accessories" in cats

    def test_check_stock(self, client, seed_data):
        p1 = seed_data["p1"]
        resp = client.get(f"/api/catalog/products/{p1.id}/stock")
        assert resp.status_code == 200
        data = resp.json()
        assert data["in_stock"] is True
        assert data["quantity"] > 0

    def test_get_related(self, client, seed_data):
        p1 = seed_data["p1"]
        resp = client.get(f"/api/catalog/products/{p1.id}/related")
        assert resp.status_code == 200
        related = resp.json()
        assert len(related) >= 1

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


class TestRelatedFallback:
    def _make_product(self, db_session, merchant_id, name, category, tags):
        from backend.models import Product
        prod = Product(
            merchant_id=merchant_id,
            name=name,
            description="test product",
            category=category,
            base_price_paise=100000,
            tags=tags,
            is_active=True
        )
        db_session.add(prod)
        db_session.flush()
        return prod

    def test_explicit_relations_preferred(self, db_session, seed_data, capsys):
        from backend.services.catalog_service import CatalogService
        p1 = seed_data["p1"]
        p3 = seed_data["p3"]
        related, source = CatalogService.get_related_products_with_source(db_session, p1.id)
        assert source == "explicit"
        assert {p.id for p in related} == {p3.id}
        assert "explicit" in capsys.readouterr().out

    def test_tag_fallback_returns_matching_accessories(self, db_session, seed_data, capsys):
        from backend.services.catalog_service import CatalogService
        merchant_id = seed_data["merchant"].id
        shoe = self._make_product(
            db_session, merchant_id, "Lone Trail", "Trail Shoes", ["trail", "running"]
        )
        self._make_product(
            db_session, merchant_id, "Trail Socks", "Accessories", ["running", "accessories"]
        )
        self._make_product(
            db_session, merchant_id, "Trail Belt", "Accessories", ["trail", "accessories"]
        )
        self._make_product(
            db_session, merchant_id, "Yoga Mat", "Accessories", ["yoga", "fitness"]
        )
        db_session.commit()

        related, source = CatalogService.get_related_products_with_source(db_session, shoe.id)
        assert source == "tag_fallback"
        assert len(related) == 2
        assert all(p.category == "Accessories" for p in related)
        assert {p.name for p in related} == {"Trail Socks", "Trail Belt"}
        assert "tag_fallback" in capsys.readouterr().out

    def test_tag_fallback_limited_to_two(self, db_session, seed_data):
        from backend.services.catalog_service import CatalogService
        merchant_id = seed_data["merchant"].id
        shoe = self._make_product(
            db_session, merchant_id, "Popular Runner", "Running Shoes", ["running"]
        )
        for i in range(4):
            self._make_product(
                db_session, merchant_id, f"Gear {i}", "Accessories", ["running", "accessories"]
            )
        db_session.commit()

        related, source = CatalogService.get_related_products_with_source(db_session, shoe.id)
        assert source == "tag_fallback"
        assert len(related) == 2

    def test_no_overlap_returns_empty(self, db_session, seed_data):
        from backend.services.catalog_service import CatalogService
        merchant_id = seed_data["merchant"].id
        odd = self._make_product(
            db_session, merchant_id, "Odd Item", "Running Shoes", ["uniquetag123"]
        )
        self._make_product(
            db_session, merchant_id, "Other Gear", "Accessories", ["different456"]
        )
        db_session.commit()

        related, source = CatalogService.get_related_products_with_source(db_session, odd.id)
        assert related == []
        assert source == "tag_fallback"

    def test_all_fifteen_products_covered(self, db_session, seed_data):
        # Mirror of the production 15-product seed (init_db.py, tag fixes
        # included): every product must have at least one upsell path.
        from backend.services.catalog_service import CatalogService
        merchant_id = seed_data["merchant"].id
        shoe_tags = [
            ["running", "marathon", "shoes", "lightweight"],
            ["running", "marathon", "shoes", "cushion"],
            ["trail", "running", "shoes", "rugged"],
            ["trail", "running", "shoes", "waterproof"],
            ["running", "shoes", "breathable", "value"],
            ["racing", "shoes", "carbon", "elite"],
            ["running", "shoes", "comfort", "daily"],
            ["racing", "shoes", "carbon", "premium"],
            ["trail", "running", "shoes", "grip", "mud"],
        ]
        acc_tags = [
            ["socks", "running", "accessories", "anti-blister"],
            ["hydration", "accessories", "belt"],
            ["safety", "accessories", "reflective"],
            ["compression", "accessories", "recovery"],
            ["insoles", "accessories", "comfort"],
            ["cap", "accessories", "sun-protection"],
        ]
        made = []
        for i, tags in enumerate(shoe_tags):
            made.append(self._make_product(
                db_session, merchant_id, f"Shoe {i}", "Running Shoes", tags
            ))
        for i, tags in enumerate(acc_tags):
            made.append(self._make_product(
                db_session, merchant_id, f"Acc {i}", "Accessories", tags
            ))
        # Mirror the 6 curated pairs from init_db.py
        made[0].related_products.append(made[9])
        made[1].related_products.append(made[10])
        made[2].related_products.append(made[8])
        made[3].related_products.append(made[2])
        made[5].related_products.append(made[9])
        made[7].related_products.append(made[13])
        db_session.commit()

        assert len(made) == 15
        for prod in made:
            related, _ = CatalogService.get_related_products_with_source(db_session, prod.id)
            assert len(related) >= 1, f"{prod.name} has no upsell path"

    @pytest.mark.asyncio
    async def test_fallback_reason_mentions_rule(self, db_session, seed_data):
        from backend.services.ai.tool_registry import create_tool_registry
        merchant_id = seed_data["merchant"].id
        shoe = self._make_product(
            db_session, merchant_id, "Lone Runner", "Running Shoes", ["running"]
        )
        self._make_product(
            db_session, merchant_id, "Run Socks", "Accessories", ["running", "accessories"]
        )
        db_session.commit()

        registry = create_tool_registry()
        result = await registry.execute(
            "get_related_products", {"product_id": shoe.id}, db=db_session
        )
        assert len(result) == 1
        assert "Commonly bought" in result[0]["reason"]
        assert "running" in result[0]["reason"]

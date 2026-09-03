import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal, engine, Base
from backend.models import Merchant, Product, ProductVariant, CommercePolicy

def seed_db():
    print("Recreating database tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        print("Seeding merchant...")
        merchant = Merchant(
            name="SprintGear India",
            email="contact@sprintgear.in",
            razorpay_key_id=""  # Can be configured later
        )
        db.add(merchant)
        db.flush()  # Get merchant.id
        
        print("Seeding commerce policy...")
        policy = CommercePolicy(
            merchant_id=merchant.id,
            max_transaction_amount_paise=500000,    # ₹5,000
            require_approval=True,
            max_quantity_per_item=5,
            allow_upsell=True,
            max_upsell_amount_paise=200000,         # ₹2,000
            allow_auto_retry=False,
            spending_limit_paise=1000000,           # ₹10,000
            is_active=True
        )
        db.add(policy)
        
        print("Seeding products...")
        # 15 Products definition
        products_data = [
            # Running Shoes
            {"id": 1, "name": "RunPro Sprint", "category": "Running Shoes", "price": 449900, "desc": "Lightweight, high-responsiveness daily running shoe ideal for marathons and fast training.", "tags": ["running", "marathon", "shoes", "lightweight"]},
            {"id": 2, "name": "UltraGlide Marathon", "category": "Running Shoes", "price": 799900, "desc": "Max cushioning premium shoe designed to provide comfort and endurance for ultra-marathons.", "tags": ["running", "marathon", "shoes", "cushion"]},
            {"id": 3, "name": "TrailBlazer X", "category": "Trail Shoes", "price": 549900, "desc": "Rugged off-road running shoe with deep lugs and a rock guard layer for technical terrains.", "tags": ["trail", "running", "shoes", "rugged"]},
            {"id": 4, "name": "TrailGrip Pro", "category": "Trail Shoes", "price": 699900, "desc": "Waterproof trail shoe with vibram outsole for ultimate grip on wet and muddy surfaces.", "tags": ["trail", "running", "shoes", "waterproof"]},
            {"id": 5, "name": "FeatherStep Lite", "category": "Running Shoes", "price": 329900, "desc": "Affordable and ultra-breathable minimal daily trainer for short, fast runs.", "tags": ["running", "shoes", "breathable", "value"]},
            {"id": 6, "name": "SpeedElite Racer", "category": "Racing Shoes", "price": 849900, "desc": "Elite racing flat with carbon composite plate for explosive energy return.", "tags": ["racing", "shoes", "carbon", "elite"]},
            {"id": 7, "name": "CushionMax Daily", "category": "Running Shoes", "price": 299900, "desc": "Pillowy soft everyday shoe with plush collar, great for recovery runs and high mileage.", "tags": ["running", "shoes", "comfort", "daily"]},
            {"id": 8, "name": "ProStride Carbon", "category": "Racing Shoes", "price": 1299900, "desc": "Pro-level carbon plated marathon shoe designed to break personal records.", "tags": ["racing", "shoes", "carbon", "premium"]},
            {"id": 9, "name": "MudRunner Grip", "category": "Trail Shoes", "price": 429900, "desc": "Aggressive lug profile designed specifically for mud and loose gravel surfaces.", "tags": ["trail", "running", "shoes", "grip", "mud"]},
            # Accessories
            {"id": 10, "name": "Performance Running Socks (3-Pack)", "category": "Accessories", "price": 49900, "desc": "Moisture-wicking, anti-blister crew socks with targeted compression zones.", "tags": ["socks", "running", "accessories", "anti-blister"]},
            {"id": 11, "name": "Hydration Running Belt", "category": "Accessories", "price": 129900, "desc": "Bounce-free belt containing two 250ml flasks and secure pouch for large phones.", "tags": ["hydration", "accessories", "belt"]},
            {"id": 12, "name": "Reflective Running Vest", "category": "Accessories", "price": 89900, "desc": "Ultra-lightweight mesh vest with high-visibility 360 reflective details for night runs.", "tags": ["safety", "accessories", "reflective"]},
            {"id": 13, "name": "Compression Calf Sleeves", "category": "Accessories", "price": 69900, "desc": "Graduated compression calf sleeves to reduce muscle fatigue and speed recovery.", "tags": ["compression", "accessories", "recovery"]},
            {"id": 14, "name": "Anti-Blister Insoles", "category": "Accessories", "price": 59900, "desc": "Anatomically shaped performance insoles with friction-reducing material.", "tags": ["insoles", "accessories", "comfort"]},
            {"id": 15, "name": "Running Cap UV Protection", "category": "Accessories", "price": 79900, "desc": "Lightweight, quick-dry cap with UPF 50+ sun protection and adjustable strap.", "tags": ["cap", "accessories", "sun-protection"]}
        ]
        
        products_map = {}
        for p_data in products_data:
            prod = Product(
                merchant_id=merchant.id,
                name=p_data["name"],
                description=p_data["desc"],
                ai_description=f"Product name: {p_data['name']}. Category: {p_data['category']}. Price: Rs. {p_data['price']/100:.2f}. Description: {p_data['desc']} Tags: {', '.join(p_data['tags'])}",
                category=p_data["category"],
                base_price_paise=p_data["price"],
                image_url=f"/placeholder-{p_data['id']}.jpg",
                tags=p_data["tags"],
                is_active=True
            )
            db.add(prod)
            products_map[p_data["id"]] = prod
        db.flush()
        
        print("Seeding product variants...")
        for p_id, prod in products_map.items():
            if prod.category in ["Running Shoes", "Trail Shoes", "Racing Shoes"]:
                # Shoe sizes 7 to 11
                for size in [7, 8, 9, 10, 11]:
                    variant = ProductVariant(
                        product_id=prod.id,
                        name=f"UK {size}",
                        sku=f"SHO-{p_id:03d}-{size}",
                        price_paise=prod.base_price_paise,
                        stock_quantity=10,
                        attributes={"size": str(size)}
                    )
                    db.add(variant)
            elif prod.name == "Performance Running Socks (3-Pack)":
                for size in ["M", "L"]:
                    variant = ProductVariant(
                        product_id=prod.id,
                        name=size,
                        sku=f"ACC-{p_id:03d}-{size}",
                        price_paise=prod.base_price_paise,
                        stock_quantity=25,
                        attributes={"size": size}
                    )
                    db.add(variant)
            else:
                # One size fits all variants
                variant = ProductVariant(
                    product_id=prod.id,
                    name="One Size",
                    sku=f"ACC-{p_id:03d}-OS",
                    price_paise=prod.base_price_paise,
                    stock_quantity=30,
                    attributes={}
                )
                db.add(variant)
        db.flush()
        
        print("Setting up related products (for upsell)...")
        # 1. RunPro Sprint (#1) -> Performance Running Socks (#10)
        products_map[1].related_products.append(products_map[10])
        # 2. UltraGlide Marathon (#2) -> Hydration Running Belt (#11)
        products_map[2].related_products.append(products_map[11])
        # 3. TrailBlazer X (#3) -> MudRunner Grip (#9)
        products_map[3].related_products.append(products_map[9])
        # 4. TrailGrip Pro (#4) -> TrailBlazer X (#3)
        products_map[4].related_products.append(products_map[3])
        # 5. SpeedElite Racer (#6) -> Performance Running Socks (#10)
        products_map[6].related_products.append(products_map[10])
        # 6. ProStride Carbon (#8) -> Anti-Blister Insoles (#14)
        products_map[8].related_products.append(products_map[14])
        
        db.commit()
        print("Database seeded successfully with SprintGear India catalog!")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()

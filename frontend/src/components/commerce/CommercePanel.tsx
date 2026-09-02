"use client";

import { ProductCard } from "@/components/commerce/ProductCard";
import { CartSummary } from "@/components/commerce/CartSummary";
import { UpsellOffer } from "@/components/commerce/UpsellOffer";
import { Product, Cart } from "@/lib/types";
import { ShoppingBag, Package, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface CommercePanelProps {
  products: Product[];
  cart: Cart | null;
  upsellProducts?: Product[];
  onAddToCart?: (product: Product) => void;
  onUpdateQuantity?: (itemId: number, quantity: number) => void;
  onRemoveItem?: (itemId: number) => void;
  onCheckout?: () => void;
}

export function CommercePanel({
  products,
  cart,
  upsellProducts = [],
  onAddToCart,
  onUpdateQuantity,
  onRemoveItem,
  onCheckout,
}: CommercePanelProps) {
  const itemCount = cart?.items?.length || 0;

  return (
    <div className="flex flex-col h-full bg-slate-950/60">
      {/* Header */}
      <div className="border-b border-slate-800 px-4 py-3 flex items-center gap-2 shrink-0">
        <ShoppingBag className="h-4 w-4 text-violet-400" />
        <h2 className="text-sm font-semibold text-white">Commerce</h2>
        {itemCount > 0 && (
          <Badge
            variant="outline"
            className="text-xs border-violet-500/30 text-violet-400 bg-violet-950/30 ml-auto"
          >
            {itemCount} {itemCount === 1 ? "item" : "items"}
          </Badge>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {/* Cart Section - Always visible at top */}
        <div className="p-4 border-b border-slate-800/50">
          <CartSummary
            cart={cart || { id: 0, session_id: "", customer_id: "", merchant_id: 1, status: "active", created_at: "", updated_at: "", items: [] }}
            onUpdateQuantity={onUpdateQuantity}
            onRemoveItem={onRemoveItem}
            onCheckout={onCheckout}
          />
        </div>

        {/* Products Section */}
        <div className="p-4">
          {products.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="h-3.5 w-3.5 text-blue-400" />
                <h3 className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Products Found
                </h3>
                <Badge variant="outline" className="text-[10px] border-slate-600 text-slate-400 ml-auto">
                  {products.length}
                </Badge>
              </div>
              <div className="space-y-3">
                {products.map((product) => (
                  <ProductCard key={product.id} product={product} onAddToCart={onAddToCart} />
                ))}
              </div>
            </div>
          )}

          {products.length === 0 && itemCount === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-center text-slate-500">
              <Package className="h-8 w-8 mb-3 text-slate-600" />
              <p className="text-sm">Products will appear here as you chat.</p>
            </div>
          )}

          {/* Upsell Section */}
          {upsellProducts.length > 0 && (
            <div className="mt-4">
              <UpsellOffer products={upsellProducts} onAddToCart={onAddToCart} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

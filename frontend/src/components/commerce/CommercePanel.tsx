"use client";

import { ProductCard } from "@/components/commerce/ProductCard";
import { Product, Cart } from "@/lib/types";
import { ShoppingBag, Package } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface CommercePanelProps {
  products: Product[];
  cart: Cart | null;
}

export function CommercePanel({ products, cart }: CommercePanelProps) {
  const itemCount = cart?.items?.length || 0;
  const totalPaise = cart?.items?.reduce((sum, item) => sum + item.unit_price_paise * item.quantity, 0) || 0;

  return (
    <div className="flex flex-col h-full bg-slate-950/40">
      <div className="border-b border-slate-800 px-4 py-3 flex items-center gap-2">
        <ShoppingBag className="h-4 w-4 text-violet-400" />
        <h2 className="text-sm font-semibold text-white">Commerce</h2>
        {itemCount > 0 && (
          <Badge variant="outline" className="text-xs border-violet-500/30 text-violet-400 bg-violet-950/20 ml-auto">
            {itemCount} items
          </Badge>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {products.length > 0 && (
          <div>
            <h3 className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-3">Products Found</h3>
            <div className="space-y-3">
              {products.map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          </div>
        )}

        {products.length === 0 && !cart && (
          <div className="flex flex-col items-center justify-center h-full text-center text-slate-500">
            <Package className="h-8 w-8 mb-3 text-slate-600" />
            <p className="text-sm">Products will appear here as you chat.</p>
          </div>
        )}

        {cart && cart.items && cart.items.length > 0 && (
          <div>
            <h3 className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-3">Your Cart</h3>
            <div className="bg-slate-800/50 rounded-lg border border-slate-700/50 p-4 space-y-3">
              {cart.items.map((item) => (
                <div key={item.id} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400">{item.quantity}x</span>
                    <span className="text-white">Product #{item.product_id}</span>
                    {item.is_upsell && (
                      <Badge variant="outline" className="text-[10px] border-amber-500/30 text-amber-400 bg-amber-950/20">
                        Upsell
                      </Badge>
                    )}
                  </div>
                  <span className="font-mono text-slate-300">
                    ₹{(item.unit_price_paise * item.quantity / 100).toLocaleString("en-IN")}
                  </span>
                </div>
              ))}
              <div className="border-t border-slate-700 pt-3 flex justify-between font-medium">
                <span className="text-white">Total</span>
                <span className="font-mono text-white">
                  ₹{(totalPaise / 100).toLocaleString("en-IN")}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

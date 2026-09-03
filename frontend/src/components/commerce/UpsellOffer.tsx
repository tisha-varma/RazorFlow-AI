"use client";

import { Product } from "@/lib/types";
import { Sparkles, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface UpsellOfferProps {
  products: Product[];
  onAddToCart?: (product: Product) => void;
}

export function UpsellOffer({ products, onAddToCart }: UpsellOfferProps) {
  if (products.length === 0) {
    return null;
  }

  return (
    <div className="bg-gradient-to-br from-amber-950/30 to-amber-900/10 rounded-lg border border-amber-500/20 overflow-hidden">
      <div className="px-4 py-3 border-b border-amber-500/10 flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-amber-400" />
        <span className="text-sm font-semibold text-amber-300">
          You might also like
        </span>
      </div>

      <div className="divide-y divide-amber-500/10">
        {products.map((product) => (
          <div key={product.id} className="px-4 py-3 flex items-center gap-3">
            <div className="flex-1 min-w-0">
              <span className="text-sm text-amber-100 truncate block">
                {product.name}
              </span>
              {product.reason && (
                <p className="text-xs italic text-amber-200/80 mt-0.5 line-clamp-2">
                  Why this fits: {product.reason}
                </p>
              )}
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-xs text-amber-400/70">
                  {product.category}
                </span>
                <span className="text-xs font-mono text-amber-300">
                  ₹{(product.base_price_paise / 100).toLocaleString("en-IN")}
                </span>
              </div>
            </div>
            {onAddToCart && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => onAddToCart(product)}
                className="shrink-0 border-amber-500/30 text-amber-400 hover:bg-amber-500/10 h-8 px-2"
              >
                <Plus className="h-3 w-3 mr-1" />
                Add
              </Button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

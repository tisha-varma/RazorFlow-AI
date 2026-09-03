"use client";

import { Product } from "@/lib/types";
import { Sparkles, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ProductImage } from "@/components/commerce/ProductImage";

interface UpsellOfferProps {
  products: Product[];
  onAddToCart?: (product: Product) => void;
}

export function UpsellOffer({ products, onAddToCart }: UpsellOfferProps) {
  if (products.length === 0) {
    return null;
  }

  return (
    <div className="bg-amber-50 rounded-xl border border-amber-200 shadow-sm overflow-hidden">
      <div className="px-4 py-3 border-b border-amber-200 bg-amber-100/60 flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-amber-600" aria-hidden="true" />
        <span className="text-sm font-semibold text-amber-900">
          You might also like
        </span>
      </div>

      <div className="divide-y divide-amber-200/70">
        {products.map((product) => (
          <div key={product.id} className="px-4 py-3 flex items-center gap-3">
            <ProductImage
              src={product.image_url}
              alt={product.name}
              className="aspect-square w-16 shrink-0 rounded-lg"
            />
            <div className="flex-1 min-w-0">
              <span className="text-[14px] font-semibold text-amber-950 block leading-snug">
                {product.name}
              </span>
              {product.reason && (
                <p className="text-[13px] italic leading-relaxed text-amber-800 mt-0.5">
                  Why this fits: {product.reason}
                </p>
              )}
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs text-amber-700">
                  {product.category}
                </span>
                <span className="text-[13px] font-bold tabular-nums text-amber-900">
                  ₹{(product.base_price_paise / 100).toLocaleString("en-IN")}
                </span>
              </div>
            </div>
            {onAddToCart && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => onAddToCart(product)}
                aria-label={`Add ${product.name} to cart`}
                className="shrink-0 border-amber-600/40 bg-white text-amber-800 hover:bg-amber-100 h-8 px-2"
              >
                <Plus className="h-3 w-3 mr-1" aria-hidden="true" />
                Add
              </Button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

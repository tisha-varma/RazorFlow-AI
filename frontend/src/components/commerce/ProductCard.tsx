"use client";

import { Product } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { ShoppingCart } from "lucide-react";
import { ProductImage } from "@/components/commerce/ProductImage";

interface ProductCardProps {
  product: Product;
  onAddToCart?: (product: Product) => void;
}

export function ProductCard({ product, onAddToCart }: ProductCardProps) {
  const formatPaise = (paise: number) =>
    `₹${(paise / 100).toLocaleString("en-IN")}`;

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow overflow-hidden flex flex-col">
      <ProductImage
        src={product.image_url}
        alt={product.name}
        className="aspect-[4/3] w-full"
      />
      <div className="p-3 flex flex-col gap-1 flex-1">
        <div className="flex items-start justify-between gap-2">
          <h4 className="text-[13px] font-semibold text-slate-900 leading-snug text-balance break-words">{product.name}</h4>
          <p className="text-[13px] font-bold text-slate-900 tabular-nums shrink-0">{formatPaise(product.base_price_paise)}</p>
        </div>
        {product.reason && (
          <p className="text-xs italic leading-snug text-indigo-700 break-words">
            {product.reason}
          </p>
        )}
        {product.description && (
          <p className="text-xs leading-snug text-slate-500 line-clamp-2 break-words">{product.description}</p>
        )}
        <div className="mt-auto pt-2">
          {onAddToCart && (
            <Button
              size="sm"
              onClick={() => onAddToCart(product)}
              aria-label={`Add ${product.name} to cart`}
              className="w-full bg-indigo-600 hover:bg-indigo-500 text-white h-8 text-[13px] touch-manipulation"
            >
              <ShoppingCart className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
              Add
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

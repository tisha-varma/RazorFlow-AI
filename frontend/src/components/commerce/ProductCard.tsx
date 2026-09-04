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
    <div className="group flex flex-col overflow-hidden rounded-xl border border-slate-200/80 bg-white shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-blue-300 hover:shadow-lg">
      <div className="relative overflow-hidden">
        <div className="transition-transform duration-500 group-hover:scale-[1.04]">
          <ProductImage
            src={product.image_url}
            alt={product.name}
            className="aspect-[4/3] w-full"
          />
        </div>
        {product.category && (
          <span className="absolute left-2 top-2 rounded-full border border-white/40 bg-slate-950/55 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white backdrop-blur-sm">
            {product.category}
          </span>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-1 p-3">
        <div className="flex items-start justify-between gap-2">
          <h4 className="text-[13px] font-semibold leading-snug text-slate-900 text-balance break-words">{product.name}</h4>
          <p className="shrink-0 rounded-lg bg-emerald-50 px-1.5 py-0.5 text-[13px] font-bold tabular-nums text-emerald-700">{formatPaise(product.base_price_paise)}</p>
        </div>
        {product.reason && (
          <p className="border-l-2 border-indigo-300 pl-2 text-xs italic leading-snug text-indigo-700 break-words">
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
              className="h-8 w-full bg-blue-700 text-[13px] text-white transition-colors hover:bg-blue-600 active:scale-[0.98] touch-manipulation"
            >
              <ShoppingCart className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
              Add
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

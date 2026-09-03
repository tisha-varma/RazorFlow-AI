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
    <div className="group flex flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.05)] transition-all duration-300 hover:-translate-y-1 hover:border-indigo-200 hover:shadow-[0_12px_32px_-8px_rgba(79,70,229,0.25)]">
      <div className="relative overflow-hidden">
        <div className="transition-transform duration-500 group-hover:scale-[1.04]">
          <ProductImage
            src={product.image_url}
            alt={product.name}
            className="aspect-[4/3] w-full"
          />
        </div>
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-slate-950/10 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
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
              className="h-8 w-full bg-gradient-to-r from-indigo-600 to-violet-600 text-[13px] text-white shadow-sm transition-all hover:from-indigo-500 hover:to-violet-500 hover:shadow-md active:scale-[0.98] touch-manipulation"
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

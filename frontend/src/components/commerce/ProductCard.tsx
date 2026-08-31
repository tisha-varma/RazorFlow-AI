"use client";

import { Product } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Package } from "lucide-react";

interface ProductCardProps {
  product: Product;
}

export function ProductCard({ product }: ProductCardProps) {
  const formatPaise = (paise: number) =>
    `₹${(paise / 100).toLocaleString("en-IN")}`;

  return (
    <div className="bg-slate-800/50 rounded-lg border border-slate-700/50 p-4 hover:border-slate-600/50 transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Package className="h-4 w-4 text-slate-400 shrink-0" />
            <h4 className="text-sm font-medium text-white truncate">{product.name}</h4>
          </div>
          <p className="text-xs text-slate-400 line-clamp-2 mb-2">{product.description}</p>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-[10px] border-slate-600 text-slate-400">
              {product.category}
            </Badge>
            {product.tags?.slice(0, 2).map((tag) => (
              <Badge key={tag} variant="outline" className="text-[10px] border-slate-600 text-slate-500">
                {tag}
              </Badge>
            ))}
          </div>
        </div>
        <div className="text-right shrink-0">
          <p className="text-sm font-bold text-white">{formatPaise(product.base_price_paise)}</p>
        </div>
      </div>
    </div>
  );
}

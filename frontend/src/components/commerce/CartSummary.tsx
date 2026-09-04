"use client";

import { Cart } from "@/lib/types";
import { ShoppingBag, Trash2, Plus, Minus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ProductImage } from "@/components/commerce/ProductImage";

interface CartSummaryProps {
  cart: Cart;
  onUpdateQuantity?: (itemId: number, quantity: number) => void;
  onRemoveItem?: (itemId: number) => void;
  onCheckout?: () => void;
}

export function CartSummary({ cart, onUpdateQuantity, onRemoveItem, onCheckout }: CartSummaryProps) {
  const items = cart.items || [];
  const itemCount = items.reduce((sum, item) => sum + item.quantity, 0);
  const subtotalPaise = items.reduce(
    (sum, item) => sum + item.unit_price_paise * item.quantity,
    0
  );
  const upsellPaise = items
    .filter((item) => item.is_upsell)
    .reduce((sum, item) => sum + item.unit_price_paise * item.quantity, 0);

  if (items.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-white/60 p-6">
        <div className="flex flex-col items-center text-center">
          <div className="w-12 h-12 rounded-xl bg-slate-100 flex items-center justify-center mb-3">
            <ShoppingBag className="h-5 w-5 text-slate-400" aria-hidden="true" />
          </div>
          <p className="text-[15px] text-slate-700 font-semibold">Your cart is empty</p>
          <p className="text-[13px] text-slate-500 mt-1">Add items to get started</p>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white shadow-[0_8px_24px_-12px_rgba(15,23,42,0.25)] overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between bg-white">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-blue-700 flex items-center justify-center">
            <ShoppingBag className="h-3.5 w-3.5 text-white" aria-hidden="true" />
          </div>
          <span className="text-[15px] font-semibold text-slate-900">Cart</span>
        </div>
        <Badge
          variant="outline"
          className="text-[11px] border-indigo-200 text-indigo-700 bg-indigo-50 px-2 py-0.5 tabular-nums"
        >
          {itemCount} {itemCount === 1 ? "item" : "items"}
        </Badge>
      </div>

      {/* Items */}
      <div className="divide-y divide-slate-100">
        {items.map((item) => (
          <div key={item.id} className="px-4 py-3">
            <div className="flex items-start gap-3">
              <ProductImage
                src={item.image_url}
                alt={item.product_name}
                className="aspect-square w-14 shrink-0 rounded-lg"
              />

              {/* Details */}
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-[14px] font-semibold text-slate-900 leading-snug">
                      {item.product_name}
                    </p>
                    {item.is_upsell && (
                      <Badge
                        variant="outline"
                        className="text-[10px] border-amber-300 text-amber-800 bg-amber-50 mt-1"
                      >
                        Upsell
                      </Badge>
                    )}
                  </div>
                  <span className="text-[14px] font-bold tabular-nums text-slate-900 shrink-0">
                    ₹{((item.unit_price_paise * item.quantity) / 100).toLocaleString("en-IN")}
                  </span>
                </div>

                {/* Quantity controls */}
                <div className="flex items-center justify-between mt-2">
                  <div className="flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 p-0.5">
                    {onUpdateQuantity && (
                      <>
                        <Button
                          variant="outline"
                          size="icon"
                          aria-label={`Decrease quantity of ${item.product_name}`}
                          className="h-7 w-7 rounded-full border-0 bg-transparent text-slate-600 shadow-none hover:bg-white hover:text-slate-900 hover:shadow-sm"
                          onClick={() => {
                            if (item.quantity <= 1) {
                              onRemoveItem?.(item.id);
                            } else {
                              onUpdateQuantity(item.id, item.quantity - 1);
                            }
                          }}
                        >
                          <Minus className="h-3 w-3" aria-hidden="true" />
                        </Button>
                        <span className="w-8 text-center text-sm font-semibold tabular-nums text-slate-900">
                          {item.quantity}
                        </span>
                        <Button
                          variant="outline"
                          size="icon"
                          aria-label={`Increase quantity of ${item.product_name}`}
                          className="h-7 w-7 rounded-full border-0 bg-transparent text-slate-600 shadow-none hover:bg-white hover:text-slate-900 hover:shadow-sm"
                          onClick={() => onUpdateQuantity(item.id, item.quantity + 1)}
                        >
                          <Plus className="h-3 w-3" aria-hidden="true" />
                        </Button>
                      </>
                    )}
                    {!onUpdateQuantity && (
                      <span className="text-[13px] text-slate-500">Qty: {item.quantity}</span>
                    )}
                  </div>

                  {onRemoveItem && (
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Remove ${item.product_name} from cart`}
                      className="h-7 w-7 text-slate-400 hover:text-red-600 hover:bg-red-50"
                      onClick={() => onRemoveItem(item.id)}
                    >
                      <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Summary — the money moment */}
      <div className="px-4 py-4 border-t border-emerald-200 bg-emerald-50">
        {upsellPaise > 0 && (
          <div className="flex justify-between text-[13px] text-slate-600 mb-1">
            <span>Upsell items</span>
            <span className="tabular-nums">+₹{(upsellPaise / 100).toLocaleString("en-IN")}</span>
          </div>
        )}
        <div className="flex justify-between items-baseline">
          <span className="text-[15px] font-semibold text-slate-700">Total</span>
          <span className="text-2xl font-bold tabular-nums text-emerald-700">
            ₹{(subtotalPaise / 100).toLocaleString("en-IN")}
          </span>
        </div>
        {onCheckout && (
          <>
            <Button
              onClick={onCheckout}
              className="w-full bg-emerald-600 hover:bg-emerald-500 text-white text-[15px] font-semibold mt-3 h-11 transition-all active:scale-[0.99]"
            >
              Proceed to Checkout
            </Button>
            <p className="mt-1.5 text-center text-[11px] font-semibold tracking-wide text-slate-400">
              TEST MODE · no real money moves
            </p>
          </>
        )}
      </div>
    </div>
  );
}

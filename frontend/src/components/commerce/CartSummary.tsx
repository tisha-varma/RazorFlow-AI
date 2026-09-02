"use client";

import { Cart } from "@/lib/types";
import { ShoppingBag, Trash2, Plus, Minus, Package } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

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
      <div className="bg-slate-800/30 rounded-xl border border-slate-700/40 p-6">
        <div className="flex flex-col items-center text-center">
          <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center mb-3">
            <ShoppingBag className="h-5 w-5 text-slate-500" />
          </div>
          <p className="text-sm text-slate-400 font-medium">Your cart is empty</p>
          <p className="text-xs text-slate-500 mt-1">Add items to get started</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-b from-slate-800/60 to-slate-800/30 rounded-xl border border-slate-700/40 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-700/40 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-violet-500/20 flex items-center justify-center">
            <ShoppingBag className="h-3.5 w-3.5 text-violet-400" />
          </div>
          <span className="text-sm font-semibold text-white">Cart</span>
        </div>
        <Badge
          variant="outline"
          className="text-[10px] border-violet-500/30 text-violet-400 bg-violet-950/30 px-2 py-0.5"
        >
          {itemCount} {itemCount === 1 ? "item" : "items"}
        </Badge>
      </div>

      {/* Items */}
      <div className="divide-y divide-slate-700/30">
        {items.map((item) => (
          <div key={item.id} className="px-4 py-3 hover:bg-slate-700/20 transition-colors">
            <div className="flex items-start gap-3">
              {/* Product icon */}
              <div className="w-10 h-10 rounded-lg bg-slate-700/50 flex items-center justify-center shrink-0">
                <Package className="h-5 w-5 text-slate-400" />
              </div>

              {/* Details */}
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-white truncate">
                      {item.product_name}
                    </p>
                    {item.is_upsell && (
                      <Badge
                        variant="outline"
                        className="text-[9px] border-amber-500/30 text-amber-400 bg-amber-950/20 mt-1"
                      >
                        Upsell
                      </Badge>
                    )}
                  </div>
                  <span className="text-sm font-semibold text-white shrink-0">
                    ₹{((item.unit_price_paise * item.quantity) / 100).toLocaleString("en-IN")}
                  </span>
                </div>

                {/* Quantity controls */}
                <div className="flex items-center justify-between mt-2">
                  <div className="flex items-center gap-1">
                    {onUpdateQuantity && (
                      <>
                        <Button
                          variant="outline"
                          size="icon"
                          className="h-7 w-7 border-slate-600 bg-slate-800 hover:bg-slate-700"
                          onClick={() => {
                            if (item.quantity <= 1) {
                              onRemoveItem?.(item.id);
                            } else {
                              onUpdateQuantity(item.id, item.quantity - 1);
                            }
                          }}
                        >
                          <Minus className="h-3 w-3" />
                        </Button>
                        <span className="w-8 text-center text-sm font-medium text-white">
                          {item.quantity}
                        </span>
                        <Button
                          variant="outline"
                          size="icon"
                          className="h-7 w-7 border-slate-600 bg-slate-800 hover:bg-slate-700"
                          onClick={() => onUpdateQuantity(item.id, item.quantity + 1)}
                        >
                          <Plus className="h-3 w-3" />
                        </Button>
                      </>
                    )}
                    {!onUpdateQuantity && (
                      <span className="text-xs text-slate-400">Qty: {item.quantity}</span>
                    )}
                  </div>

                  {onRemoveItem && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-slate-500 hover:text-red-400 hover:bg-red-500/10"
                      onClick={() => onRemoveItem(item.id)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="px-4 py-3 border-t border-slate-700/40 bg-slate-800/20">
        {upsellPaise > 0 && (
          <div className="flex justify-between text-xs text-slate-400 mb-1">
            <span>Upsell items</span>
            <span className="font-mono">+₹{(upsellPaise / 100).toLocaleString("en-IN")}</span>
          </div>
        )}
        <div className="flex justify-between items-baseline">
          <span className="text-sm text-slate-300">Total</span>
          <span className="text-lg font-bold text-white">
            ₹{(subtotalPaise / 100).toLocaleString("en-IN")}
          </span>
        </div>
        {onCheckout && (
          <Button
            onClick={onCheckout}
            className="w-full bg-violet-600 hover:bg-violet-500 text-white text-sm mt-3 h-10"
          >
            Proceed to Checkout
          </Button>
        )}
      </div>
    </div>
  );
}

"use client";

import { ProductCard } from "@/components/commerce/ProductCard";
import { CartSummary } from "@/components/commerce/CartSummary";
import { UpsellOffer } from "@/components/commerce/UpsellOffer";
import { PaymentBox } from "@/components/commerce/PaymentBox";
import ApprovalScreen from "@/components/commerce/ApprovalScreen";
import { Product, Cart } from "@/lib/types";
import { ShoppingBag, Package, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface PaidOrder {
  order_id: number;
  order_number: string;
  total_paise: number;
}

interface CommercePanelProps {
  products: Product[];
  cart: Cart | null;
  upsellProducts?: Product[];
  approvalId?: number | null;
  approvalToken?: string | null;
  approvedId?: number | null;
  sessionId?: string;
  onAddToCart?: (product: Product) => void;
  onUpdateQuantity?: (itemId: number, quantity: number) => void;
  onRemoveItem?: (itemId: number) => void;
  onCheckout?: () => void;
  onApprovalComplete?: () => void;
  onApprovalRejected?: () => void;
  onPaid?: (order: PaidOrder) => void;
}

export function CommercePanel({
  products,
  cart,
  upsellProducts = [],
  approvalId = null,
  approvalToken = null,
  approvedId = null,
  sessionId = "",
  onAddToCart,
  onUpdateQuantity,
  onRemoveItem,
  onCheckout,
  onApprovalComplete,
  onApprovalRejected,
  onPaid,
}: CommercePanelProps) {
  const itemCount = cart?.items?.length || 0;

  return (
    <div className="flex flex-col h-full bg-stone-100">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-4 py-3 flex items-center gap-2 shrink-0 shadow-sm">
        <ShoppingBag className="h-4 w-4 text-indigo-600" aria-hidden="true" />
        <h2 className="text-[15px] font-semibold text-slate-900">Commerce</h2>
        {itemCount > 0 && (
          <Badge
            variant="outline"
            className="text-xs border-indigo-200 text-indigo-700 bg-indigo-50 ml-auto"
          >
            {itemCount} {itemCount === 1 ? "item" : "items"}
          </Badge>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {/* Approval Section - Shows when approval is pending */}
        {approvalId && sessionId && (
          <div className="p-4">
            <ApprovalScreen
              approvalId={approvalId}
              approvalToken={approvalToken}
              sessionId={sessionId}
              onApprove={() => onApprovalComplete?.()}
              onReject={() => onApprovalRejected?.()}
            />
          </div>
        )}

        {/* Payment Section - Shows after the customer approves */}
        {approvedId && sessionId && (
          <div className="p-4">
            <PaymentBox
              approvalId={approvedId}
              sessionId={sessionId}
              onPaid={onPaid}
            />
          </div>
        )}

        {/* Cart Section - Always visible at top */}
        <div className="p-4">
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
                <Sparkles className="h-3.5 w-3.5 text-indigo-600" aria-hidden="true" />
                <h3 className="text-[13px] font-semibold text-slate-700 uppercase tracking-wider">
                  Products Found
                </h3>
                <Badge variant="outline" className="text-[11px] border-slate-300 text-slate-600 bg-white ml-auto">
                  {products.length}
                </Badge>
              </div>
              <div className="grid grid-cols-2 xl:grid-cols-3 gap-3">
                {products.map((product) => (
                  <ProductCard key={product.id} product={product} onAddToCart={onAddToCart} />
                ))}
              </div>
            </div>
          )}

          {products.length === 0 && itemCount === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-center" aria-live="polite">
              <span className="flex h-12 w-12 items-center justify-center rounded-full bg-indigo-50 mb-3">
                <Package className="h-6 w-6 text-indigo-400" aria-hidden="true" />
              </span>
              <p className="text-[15px] font-semibold text-slate-700">Waiting for your request…</p>
              <p className="mt-1 max-w-[240px] text-[13px] leading-relaxed text-slate-500">
                Ask for anything — shoes, budgets, comparisons. Matching products land here.
              </p>
              <div className="mt-3 flex flex-wrap justify-center gap-1.5">
                {["Marathon shoes", "Trail gear", "Under ₹5,000"].map((hint) => (
                  <span
                    key={hint}
                    className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[11px] text-slate-500"
                  >
                    {hint}
                  </span>
                ))}
              </div>
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

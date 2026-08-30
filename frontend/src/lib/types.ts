export interface Merchant {
  id: number;
  name: string;
  email: string;
  razorpay_key_id?: string;
  created_at: string;
}

export interface ProductVariant {
  id: number;
  product_id: number;
  name: string;
  sku: string;
  price_paise: number;
  stock_quantity: number;
  attributes: Record<string, string>;
}

export interface Product {
  id: number;
  merchant_id: number;
  name: string;
  description?: string;
  ai_description?: string;
  category: string;
  base_price_paise: number;
  image_url?: string;
  tags: string[];
  is_active: boolean;
  created_at: string;
  variants?: ProductVariant[];
  related_products?: Product[];
}

export interface CartItem {
  id: number;
  cart_id: number;
  product_id: number;
  variant_id?: number;
  quantity: number;
  unit_price_paise: number;
  is_upsell: boolean;
  created_at: string;
  product?: Product;
  variant?: ProductVariant;
}

export interface Cart {
  id: number;
  session_id: string;
  customer_id: string;
  merchant_id: number;
  status: "active" | "checked_out" | "abandoned";
  created_at: string;
  updated_at: string;
  items?: CartItem[];
}

export interface CommercePolicy {
  id: number;
  merchant_id: number;
  max_transaction_amount_paise: number;
  require_approval: boolean;
  max_quantity_per_item: number;
  allow_upsell: boolean;
  max_upsell_amount_paise: number;
  allow_auto_retry: boolean;
  spending_limit_paise: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface OrderItem {
  id: number;
  order_id: number;
  product_id: number;
  variant_id?: number;
  product_name: string;
  quantity: number;
  unit_price_paise: number;
  total_paise: number;
  is_upsell: boolean;
}

export interface RazorpayPayment {
  id: number;
  order_id: number;
  razorpay_order_id: string;
  razorpay_payment_id?: string;
  razorpay_signature?: string;
  amount_paise: number;
  currency: string;
  status: "created" | "authorized" | "captured" | "failed" | "refunded";
  method?: string;
  error_code?: string;
  error_description?: string;
  verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface Order {
  id: number;
  order_number: string;
  merchant_id: number;
  customer_id: string;
  session_id: string;
  cart_id: number;
  subtotal_paise: number;
  total_paise: number;
  status: "pending" | "paid" | "failed" | "cancelled";
  is_ai_assisted: boolean;
  upsell_revenue_paise: number;
  razorpay_order_id?: string;
  created_at: string;
  items?: OrderItem[];
  payments?: RazorpayPayment[];
}

export interface Approval {
  id: number;
  session_id: string;
  order_id?: number;
  cart_id: number;
  requested_amount_paise: number;
  status: "pending" | "approved" | "rejected" | "expired";
  summary_json: any;
  approved_at?: string;
  created_at: string;
  cart?: Cart;
}

export interface AuditEvent {
  id: number;
  session_id?: string;
  merchant_id: number;
  event_type: string;
  event_data: any;
  actor: "user" | "ai" | "system";
  timestamp: string;
  related_entity_type?: string;
  related_entity_id?: number;
}

export interface DashboardMetrics {
  total_revenue_paise: number;
  ai_assisted_revenue_paise: number;
  upsell_revenue_paise: number;
  total_orders: number;
  ai_assisted_orders: number;
  avg_order_value_paise: number;
  conversion_rate: number;
}

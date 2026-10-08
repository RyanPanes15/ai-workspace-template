export interface OrderInput { orderDate: string; deliveryDate: string; qty: number }

export function validateOrder(o: OrderInput): string[] {
  const errs: string[] = [];
  if (!o.orderDate) {
    errs.push('order date required');
  }
  if (o.deliveryDate && o.deliveryDate < o.orderDate) {
    errs.push('delivery date before order date');
  }
  if (o.qty <= 0) {
    errs.push('qty must be positive');
  }
  return errs;
}

export const normalizeQty = (q: number): number => Math.max(0, Math.round(q));

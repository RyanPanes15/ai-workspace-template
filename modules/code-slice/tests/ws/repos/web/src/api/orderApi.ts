import { http } from './http';

export async function saveOrder(payload: Record<string, unknown>): Promise<string> {
  const res = await http.post('/orders', payload);
  return res.data.id;
}

export async function fetchOrder(id: string) {
  const res = await http.get(`/orders/${id}`);
  return res.data;
}

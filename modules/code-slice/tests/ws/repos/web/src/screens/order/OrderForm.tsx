import React, { useEffect, useState } from 'react';
import { validateOrder, normalizeQty } from './validation';
import { saveOrder, fetchOrder } from '@api/orderApi';

type Props = { orderId?: string; onSaved: (id: string) => void };

/** Order entry form. */
export const OrderForm: React.FC<Props> = ({ orderId, onSaved }) => {
  const [orderDate, setOrderDate] = useState<string>('');
  const [deliveryDate, setDeliveryDate] = useState<string>('');
  const [qty, setQty] = useState<number>(0);
  const [errors, setErrors] = useState<string[]>([]);

  useEffect(() => {
    if (!orderId) {
      return;
    }
    fetchOrder(orderId).then((o) => {
      setOrderDate(o.orderDate);
      setDeliveryDate(o.deliveryDate);
      setQty(o.qty);
    });
  }, [orderId]);

  const handleSubmit = async () => {
    const errs = validateOrder({ orderDate, deliveryDate, qty });
    if (errs.length > 0) {
      setErrors(errs);
      return;
    }
    const payload = {
      orderDate,
      deliveryDate,
      qty: normalizeQty(qty),
      source: 'web',
      channel: 'form',
      priority: 1,
      notes: '',
    };
    try {
      const id = await saveOrder(payload);
      onSaved(id);
    } catch (e) {
      setErrors(['save failed']);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <label>Order date</label>
      <input value={orderDate} onChange={(e) => setOrderDate(e.target.value)} />
      <label>Delivery date</label>
      <input
        value={deliveryDate}
        min={orderDate}
        onChange={(e) => setDeliveryDate(e.target.value)}
      />
      <input value={qty} onChange={(e) => setQty(Number(e.target.value))} />
      {errors.map((er) => (
        <p key={er}>{er}</p>
      ))}
      <button type="submit">Save</button>
    </form>
  );
};

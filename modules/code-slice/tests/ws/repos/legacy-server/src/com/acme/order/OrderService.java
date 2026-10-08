package com.acme.order;

import java.util.Date;

public class OrderService {

    private final OrderDao dao;

    public OrderService(OrderDao dao) {
        this.dao = dao;
    }

    /**
     * Saves an order. Delivery date must not precede the order date.
     */
    public String save(Order order) {
        if (order.getDeliveryDate() != null && order.getDeliveryDate().before(order.getOrderDate())) {
            throw new IllegalArgumentException("delivery before order");
        }
        String id = dao.insert(order);
        audit(id);
        return id;
    }

    private void audit(String id) {
        System.out.println("saved " + id);
    }
}

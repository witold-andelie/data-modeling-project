-- Customer order overview, one row per order; no line/payment fan-out.
SELECT o.order_id, o.status, REPLACE(CAST(o.purchased_at AS CHAR), ' ', 'T') AS purchased_at,
       COALESCE(p.payment_total_cents, 0) AS payment_total_cents
FROM orders o
JOIN customer_records cr ON cr.record_id = o.record_id
LEFT JOIN (SELECT order_id, SUM(amount_cents) AS payment_total_cents
           FROM payments GROUP BY order_id) p ON p.order_id = o.order_id
WHERE cr.customer_id = %(customer_id)s
  AND o.purchased_at >= %(start)s AND o.purchased_at < %(end)s
ORDER BY o.order_id;

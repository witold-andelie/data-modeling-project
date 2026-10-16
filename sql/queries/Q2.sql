-- Retrospective customer totals; all statuses; paid amount is not profit or revenue.
SELECT cr.customer_id, COUNT(*) AS order_count,
       COALESCE(SUM(p.amount_cents), 0) AS payment_total_cents
FROM orders o JOIN customer_records cr ON cr.record_id = o.record_id
LEFT JOIN (SELECT order_id, SUM(amount_cents) AS amount_cents FROM payments GROUP BY order_id) p
  ON p.order_id = o.order_id
WHERE o.purchased_at >= %(start)s AND o.purchased_at < %(end)s
GROUP BY cr.customer_id
ORDER BY cr.customer_id;

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchOrders } from "../api/orders";
import LoadingSpinner from "../components/LoadingSpinner";
import OrderStatusBadge from "../components/OrderStatusBadge";
import { useCart } from "../context/CartContext";

const priceFormatter = new Intl.NumberFormat("ko-KR");

export default function OrdersPage() {
  const { sessionId } = useCart();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchOrders(sessionId)
      .then(setOrders)
      .finally(() => setLoading(false));
  }, [sessionId]);

  return (
    <div className="page">
      <section className="section">
        <div className="section-header">
          <div>
            <h1>주문 내역</h1>
            <p>현재 브라우저 세션으로 생성한 주문 목록입니다.</p>
          </div>
        </div>

        {loading && <LoadingSpinner />}
        {!loading && orders.length === 0 && <p className="empty-text">아직 주문 내역이 없습니다.</p>}

        <div className="order-list">
          {orders.map((order) => (
            <Link className="order-card" key={order.id} to={`/orders/${order.order_number}`}>
              <div>
                <strong>{order.order_number}</strong>
                <span>{new Date(order.created_at).toLocaleString("ko-KR")}</span>
              </div>
              <OrderStatusBadge status={order.status} />
              <strong>{priceFormatter.format(order.total_price)}원</strong>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}

import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchOrder } from "../api/orders";
import LoadingSpinner from "../components/LoadingSpinner";
import OrderStatusBadge from "../components/OrderStatusBadge";

const priceFormatter = new Intl.NumberFormat("ko-KR");

export default function OrderDetailPage() {
  const { orderNumber } = useParams();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchOrder(orderNumber)
      .then(setOrder)
      .finally(() => setLoading(false));
  }, [orderNumber]);

  if (loading) return <LoadingSpinner label="주문 정보를 불러오는 중입니다" />;
  if (!order) return <p className="empty-text">주문을 찾을 수 없습니다.</p>;

  return (
    <div className="page">
      <section className="order-complete">
        <span className="eyebrow">주문 완료</span>
        <h1>주문이 접수되었습니다</h1>
        <p>주문번호 {order.order_number}</p>
        <OrderStatusBadge status={order.status} />
        <div className="hero-actions">
          <Link className="button primary" to="/products">
            계속 쇼핑하기
          </Link>
          <Link className="button secondary" to="/orders">
            주문 내역 보기
          </Link>
        </div>
      </section>

      <section className="section order-detail-grid">
        <div>
          <div className="section-header">
            <h2>주문 상품</h2>
          </div>
          <div className="cart-list">
            {order.items.map((item) => (
              <article className="cart-item" key={item.id}>
                <img src={item.image_url} alt={item.product_name} />
                <div>
                  <strong>{item.product_name}</strong>
                  <p>{item.brand}</p>
                  <span>{priceFormatter.format(item.price)}원 × {item.quantity}</span>
                </div>
                <div className="cart-subtotal">{priceFormatter.format(item.subtotal)}원</div>
              </article>
            ))}
          </div>
        </div>

        <aside className="checkout-summary">
          <h2>배송/결제 정보</h2>
          <dl>
            <div>
              <dt>주문자</dt>
              <dd>{order.customer_name}</dd>
            </div>
            <div>
              <dt>전화번호</dt>
              <dd>{order.phone}</dd>
            </div>
            <div>
              <dt>주소</dt>
              <dd>{order.address}</dd>
            </div>
            <div>
              <dt>요청사항</dt>
              <dd>{order.delivery_memo || "없음"}</dd>
            </div>
            <div>
              <dt>결제 방식</dt>
              <dd>{order.payment_method}</dd>
            </div>
          </dl>
          <div className="summary-total">
            <span>총 결제 금액</span>
            <strong>{priceFormatter.format(order.total_price)}원</strong>
          </div>
        </aside>
      </section>
    </div>
  );
}

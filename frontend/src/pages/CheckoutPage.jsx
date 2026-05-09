import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { createOrder } from "../api/orders";
import { useCart } from "../context/CartContext";

const priceFormatter = new Intl.NumberFormat("ko-KR");

export default function CheckoutPage() {
  const navigate = useNavigate();
  const { cart, sessionId, refreshCart } = useCart();
  const [form, setForm] = useState({
    customer_name: "",
    phone: "",
    address: "",
    delivery_memo: "",
    payment_method: "카드결제 시뮬레이션",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }));

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const order = await createOrder({ ...form, session_id: sessionId });
      await refreshCart();
      navigate(`/orders/${order.order_number}`);
    } catch (err) {
      setError(err.message || "주문 생성에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  if (cart.items.length === 0) {
    return (
      <div className="page">
        <section className="section">
          <h1>주문서</h1>
          <p className="empty-text">
            장바구니가 비어 있습니다. <Link to="/products">상품을 먼저 담아주세요.</Link>
          </p>
        </section>
      </div>
    );
  }

  return (
    <div className="page checkout-page">
      <section className="section">
        <div className="section-header">
          <div>
            <h1>주문서 작성</h1>
            <p>캡스톤 시연용 결제 시뮬레이션입니다. 실제 결제는 발생하지 않습니다.</p>
          </div>
        </div>

        {error && <p className="error-text">{error}</p>}

        <form className="checkout-form" onSubmit={submit}>
          <label>
            주문자 이름
            <input value={form.customer_name} onChange={(event) => update("customer_name", event.target.value)} />
          </label>
          <label>
            전화번호
            <input value={form.phone} onChange={(event) => update("phone", event.target.value)} />
          </label>
          <label className="checkout-wide">
            주소
            <input value={form.address} onChange={(event) => update("address", event.target.value)} />
          </label>
          <label className="checkout-wide">
            배송 요청사항
            <input value={form.delivery_memo} onChange={(event) => update("delivery_memo", event.target.value)} />
          </label>
          <label>
            결제 방식
            <select value={form.payment_method} onChange={(event) => update("payment_method", event.target.value)}>
              <option>카드결제 시뮬레이션</option>
              <option>간편결제 시뮬레이션</option>
              <option>무통장입금</option>
            </select>
          </label>
          <button className="button primary checkout-wide" type="submit" disabled={loading}>
            {loading ? "주문 처리 중" : "결제 시뮬레이션 완료"}
          </button>
        </form>
      </section>

      <aside className="section checkout-summary">
        <h2>주문 상품</h2>
        {cart.items.map((item) => (
          <div className="summary-item" key={item.id}>
            <span>{item.product.name}</span>
            <strong>{item.quantity}개</strong>
            <em>{priceFormatter.format(item.subtotal)}원</em>
          </div>
        ))}
        <div className="summary-total">
          <span>총 결제 금액</span>
          <strong>{priceFormatter.format(cart.total_price)}원</strong>
        </div>
      </aside>
    </div>
  );
}

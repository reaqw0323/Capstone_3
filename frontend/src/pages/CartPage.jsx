import { Link } from "react-router-dom";
import LoadingSpinner from "../components/LoadingSpinner";
import { useCart } from "../context/CartContext";

const priceFormatter = new Intl.NumberFormat("ko-KR");

export default function CartPage() {
  const { cart, loading, changeQuantity, removeFromCart, clearCart } = useCart();

  return (
    <div className="page">
      <section className="section">
        <div className="section-header">
          <div>
            <h1>장바구니</h1>
            <p>선택한 상품의 수량과 합계를 확인하세요.</p>
          </div>
          {cart.items.length > 0 && (
            <button className="button secondary" type="button" onClick={clearCart}>
              전체 비우기
            </button>
          )}
        </div>

        {loading && <LoadingSpinner label="장바구니를 불러오는 중입니다" />}

        {!loading && cart.items.length === 0 && (
          <div className="empty-text">
            장바구니가 비어 있습니다. <Link to="/products">상품 보러가기</Link>
          </div>
        )}

        {cart.items.length > 0 && (
          <div className="cart-layout">
            <div className="cart-list">
              {cart.items.map((item) => (
                <article className="cart-item" key={item.id}>
                  <img src={item.product.image_url} alt={item.product.name} />
                  <div>
                    <strong>{item.product.name}</strong>
                    <p>{item.product.brand} · 재고 {item.product.stock}</p>
                    <span>{priceFormatter.format(item.product.price)}원</span>
                  </div>
                  <div className="quantity-control">
                    <button
                      className="button secondary"
                      type="button"
                      disabled={item.quantity <= 1}
                      onClick={() => changeQuantity(item.id, item.quantity - 1)}
                    >
                      -
                    </button>
                    <strong>{item.quantity}</strong>
                    <button
                      className="button secondary"
                      type="button"
                      disabled={item.quantity >= item.product.stock}
                      onClick={() => changeQuantity(item.id, item.quantity + 1)}
                    >
                      +
                    </button>
                  </div>
                  <div className="cart-subtotal">{priceFormatter.format(item.subtotal)}원</div>
                  <button className="button danger" type="button" onClick={() => removeFromCart(item.id)}>
                    삭제
                  </button>
                </article>
              ))}
            </div>

            <aside className="checkout-summary">
              <h2>주문 금액</h2>
              <dl>
                <div>
                  <dt>상품 수량</dt>
                  <dd>{cart.total_quantity}개</dd>
                </div>
                <div>
                  <dt>상품 합계</dt>
                  <dd>{priceFormatter.format(cart.total_price)}원</dd>
                </div>
                <div>
                  <dt>배송비</dt>
                  <dd>0원</dd>
                </div>
              </dl>
              <div className="summary-total">
                <span>총 결제 금액</span>
                <strong>{priceFormatter.format(cart.total_price)}원</strong>
              </div>
              <Link className="button primary full-button" to="/checkout">
                주문하기
              </Link>
            </aside>
          </div>
        )}
      </section>
    </div>
  );
}

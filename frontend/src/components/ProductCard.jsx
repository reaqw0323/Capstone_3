import { Link } from "react-router-dom";
import { useCart } from "../context/CartContext";
import { useCompare } from "../context/CompareContext";

const priceFormatter = new Intl.NumberFormat("ko-KR");

export default function ProductCard({ product }) {
  const { compareIds, toggleCompare } = useCompare();
  const { addToCart } = useCart();
  const selected = compareIds.includes(product.id);

  return (
    <article className="product-card">
      <Link to={`/products/${product.id}`} className="product-image-link">
        <img src={product.image_url} alt={product.name} className="product-image" />
      </Link>
      <div className="product-card-body">
        <div className="product-meta">
          <span>{product.brand}</span>
          <span>{product.category}</span>
        </div>
        <Link to={`/products/${product.id}`} className="product-title">
          {product.name}
        </Link>
        <p className="product-description">{product.short_description}</p>
        <div className="product-price">{priceFormatter.format(product.price)}원</div>
        <div className="rating-row">
          <span>평점 {product.rating}</span>
          <span>리뷰 {product.review_count}</span>
        </div>
        <div className="card-actions">
          <button
            className={selected ? "button secondary active" : "button secondary"}
            onClick={() => toggleCompare(product.id)}
            type="button"
          >
            {selected ? "비교 해제" : "비교 담기"}
          </button>
          <Link className="button primary" to={`/products/${product.id}`}>
            상세보기
          </Link>
          <button className="button primary" type="button" onClick={() => addToCart(product.id, 1)}>
            장바구니
          </button>
        </div>
      </div>
    </article>
  );
}

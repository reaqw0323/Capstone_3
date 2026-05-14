import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { requestReviewSummary } from "../api/ai";
import { fetchProduct, fetchProductReviews } from "../api/products";
import LoadingSpinner from "../components/LoadingSpinner";
import { useCart } from "../context/CartContext";
import { useCompare } from "../context/CompareContext";

const priceFormatter = new Intl.NumberFormat("ko-KR");

export default function ProductDetailPage() {
  const { id } = useParams();
  const productId = Number(id);
  const { compareIds, toggleCompare } = useCompare();
  const { addToCart, lastMessage, setLastMessage } = useCart();
  const [product, setProduct] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [summary, setSummary] = useState("");
  const [loading, setLoading] = useState(true);
  const [summaryLoading, setSummaryLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchProduct(productId), fetchProductReviews(productId)])
      .then(([productData, reviewData]) => {
        setProduct(productData);
        setReviews(reviewData);
      })
      .finally(() => setLoading(false));
  }, [productId]);

  const summarize = async () => {
    setSummaryLoading(true);
    try {
      const result = await requestReviewSummary(productId);
      setSummary(result.answer);
    } finally {
      setSummaryLoading(false);
    }
  };

  if (loading) return <LoadingSpinner />;
  if (!product) return <p className="empty-text">상품을 찾을 수 없습니다.</p>;

  const selected = compareIds.includes(product.id);
  const addCurrentProduct = async () => {
    await addToCart(product.id, 1);
    setTimeout(() => setLastMessage(""), 1800);
  };
  const detailSections = [
    ["상세설명", product.detail_description],
    ["추천대상", product.recommended_for],
    ["주의사항", product.cautions],
  ].filter(([, value]) => value && String(value).trim());

  return (
    <div className="page">
      <section className="detail-layout">
        <div className="detail-image-wrap">
          <img src={product.image_url} alt={product.name} />
        </div>
        <div className="detail-info">
          <span className="eyebrow">{product.category}</span>
          <h1>{product.name}</h1>
          <p>{product.short_description}</p>
          <div className="detail-price">{priceFormatter.format(product.price)}원</div>
          <div className="rating-row">
            <span>브랜드 {product.brand}</span>
            <span>평점 {product.rating}</span>
            <span>리뷰 {product.review_count}</span>
            <span>재고 {product.stock}</span>
          </div>
          <div className="hero-actions">
            <button
              className={selected ? "button secondary active" : "button secondary"}
              type="button"
              onClick={() => toggleCompare(product.id)}
            >
              {selected ? "비교 해제" : "비교 담기"}
            </button>
            <button className="button primary" type="button" onClick={addCurrentProduct}>
              장바구니 담기
            </button>
            <Link
              className="button secondary"
              to={`/ai?message=${encodeURIComponent(`${product.name}에 대해 알려줘`)}`}
            >
              AI에게 물어보기
            </Link>
          </div>
          {lastMessage && <p className="success-text">{lastMessage}</p>}
        </div>
      </section>

      {!!detailSections.length && (
        <section className="section product-extra-info">
          {detailSections.map(([title, value]) => (
            <div key={title}>
              <h2>{title}</h2>
              <p>{value}</p>
            </div>
          ))}
        </section>
      )}

      <section className="section detail-grid">
        <div>
          <div className="section-header">
            <h2>주요 스펙</h2>
          </div>
          <dl className="spec-list">
            {Object.entries(product.specs).map(([key, value]) => (
              <div key={key}>
                <dt>{key}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        </div>
        <div>
          <div className="section-header">
            <h2>AI 리뷰 요약</h2>
            <button className="button secondary" onClick={summarize} disabled={summaryLoading} type="button">
              요약하기
            </button>
          </div>
          {summaryLoading && <LoadingSpinner label="리뷰를 요약하고 있습니다" />}
          {summary && <div className="ai-result-box">{summary}</div>}
          {!summary && !summaryLoading && <p className="empty-text">리뷰 요약 버튼을 눌러 AI 요약을 확인하세요.</p>}
        </div>
      </section>

      <section className="section">
        <div className="section-header">
          <h2>리뷰</h2>
        </div>
        <div className="review-list">
          {reviews.map((review) => (
            <article className="review-item" key={review.id}>
              <strong>{review.user_name} · 평점 {review.rating}</strong>
              <p>{review.content}</p>
              <span>장점: {review.pros}</span>
              <span>아쉬운 점: {review.cons}</span>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

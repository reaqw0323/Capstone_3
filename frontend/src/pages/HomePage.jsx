import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { fetchCategories, fetchProducts } from "../api/products";
import ProductCard from "../components/ProductCard";
import LoadingSpinner from "../components/LoadingSpinner";

export default function HomePage() {
  const navigate = useNavigate();
  const [keyword, setKeyword] = useState("");
  const [categories, setCategories] = useState([]);
  const [featured, setFeatured] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchCategories(), fetchProducts({ sort: "rating" })])
      .then(([categoryData, productData]) => {
        setCategories(categoryData);
        setFeatured(productData.slice(0, 6));
      })
      .finally(() => setLoading(false));
  }, []);

  const submit = (event) => {
    event.preventDefault();
    navigate(`/products?query=${encodeURIComponent(keyword)}`);
  };

  return (
    <div className="page">
      <section className="home-hero">
        <div className="hero-copy">
          <span className="eyebrow">로컬 LLM 기반 쇼핑 추천</span>
          <h1>EasyPick AI</h1>
          <p>
            상품 DB와 리뷰 데이터만 근거로 비교하고 추천하는 캡스톤 쇼핑 플랫폼입니다.
          </p>
          <form className="hero-search" onSubmit={submit}>
            <input
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
              placeholder="무선청소기, 게임용 모니터, 부모님 공기청정기"
            />
            <button className="button primary" type="submit">
              검색
            </button>
          </form>
          <div className="hero-actions">
            <Link className="button primary" to="/ai">
              AI 쇼핑 도우미
            </Link>
            <Link className="button secondary" to="/products">
              전체 상품 보기
            </Link>
          </div>
        </div>
        <div className="hero-panel" aria-label="시연 흐름">
          <strong>발표 시연 추천 흐름</strong>
          <ol>
            <li>무선청소기 검색</li>
            <li>20만 원 이하 필터 적용</li>
            <li>2~3개 비교 담기</li>
            <li>AI 비교 설명 요청</li>
          </ol>
        </div>
      </section>

      <section className="section">
        <div className="section-header">
          <h2>카테고리</h2>
        </div>
        <div className="category-grid">
          {categories.map((category) => (
            <Link key={category.id} to={`/products?category=${category.name}`} className="category-tile">
              <strong>{category.name}</strong>
              <span>{category.description}</span>
            </Link>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="section-header">
          <h2>추천 상품</h2>
          <Link to="/products">더 보기</Link>
        </div>
        {loading ? (
          <LoadingSpinner />
        ) : (
          <div className="product-grid">
            {featured.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

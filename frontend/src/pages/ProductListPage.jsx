import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { fetchCategories, fetchProducts } from "../api/products";
import LoadingSpinner from "../components/LoadingSpinner";
import ProductCard from "../components/ProductCard";
import ProductFilter from "../components/ProductFilter";
import { useCompare } from "../context/CompareContext";

function filtersFromParams(searchParams) {
  return {
    query: searchParams.get("query") || "",
    category: searchParams.get("category") || "",
    minPrice: searchParams.get("minPrice") || "",
    maxPrice: searchParams.get("maxPrice") || "",
    brand: searchParams.get("brand") || "",
    sort: searchParams.get("sort") || "rating",
  };
}

export default function ProductListPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [filters, setFilters] = useState(() => filtersFromParams(searchParams));
  const [categories, setCategories] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { compareIds } = useCompare();

  useEffect(() => {
    setFilters(filtersFromParams(searchParams));
  }, [searchParams]);

  useEffect(() => {
    setLoading(true);
    setError("");
    Promise.all([fetchCategories(), fetchProducts(filters)])
      .then(([categoryData, productData]) => {
        setCategories(categoryData);
        setProducts(productData);
      })
      .catch(() => setError("상품 목록을 불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }, [filters]);

  const submit = (event) => {
    event.preventDefault();
    const next = {};
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== "") next[key] = value;
    });
    setSearchParams(next);
  };

  return (
    <div className="page two-column">
      <aside>
        <ProductFilter categories={categories} filters={filters} onChange={setFilters} onSubmit={submit} />
        <div className="compare-shortcut">
          <strong>비교 선택 {compareIds.length}개</strong>
          <Link className="button secondary" to="/compare">
            비교 페이지로 이동
          </Link>
        </div>
      </aside>

      <section>
        <div className="section-header">
          <div>
            <h1>상품 목록</h1>
            <p>{products.length}개 상품이 검색되었습니다.</p>
          </div>
        </div>
        {loading && <LoadingSpinner />}
        {error && <p className="error-text">{error}</p>}
        {!loading && products.length === 0 && <p className="empty-text">조건에 맞는 상품이 없습니다.</p>}
        <div className="product-grid list-grid">
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      </section>
    </div>
  );
}

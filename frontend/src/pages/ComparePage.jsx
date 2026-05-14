import { useEffect, useState } from "react";
import { fetchCompareProducts } from "../api/products";
import LoadingSpinner from "../components/LoadingSpinner";
import ProductCompareTable from "../components/ProductCompareTable";
import { useAiState } from "../context/AiStateContext";
import { useCompare } from "../context/CompareContext";

export default function ComparePage() {
  const { compareIds, clearCompare } = useCompare();
  const { compareTask, compareMatches, startCompare } = useAiState();
  const [products, setProducts] = useState([]);
  const [criteria, setCriteria] = useState("가격, 스펙, 평점, 리뷰 기준으로 비교해줘");
  const [loading, setLoading] = useState(false);
  const selectedCategories = Array.from(new Set(products.map((product) => product.category).filter(Boolean)));
  const hasMixedCategories = selectedCategories.length > 1;
  const currentCompareTask = compareMatches(compareIds) ? compareTask : null;
  const aiLoading = currentCompareTask?.status === "loading";
  const aiAnswer = currentCompareTask?.status === "done" ? currentCompareTask.answer : "";
  const aiError = currentCompareTask?.status === "error" ? currentCompareTask.error : "";

  useEffect(() => {
    if (compareIds.length === 0) {
      setProducts([]);
      return;
    }
    setLoading(true);
    fetchCompareProducts(compareIds)
      .then(setProducts)
      .finally(() => setLoading(false));
  }, [compareIds]);

  const askAi = async () => {
    if (hasMixedCategories) return;
    await startCompare(compareIds, criteria);
  };

  return (
    <div className="page">
      <section className="section">
        <div className="section-header">
          <div>
            <h1>상품 비교</h1>
            <p>선택한 상품을 표로 비교하고 AI 설명을 요청할 수 있습니다.</p>
          </div>
          <button className="button secondary" onClick={clearCompare} type="button">
            선택 비우기
          </button>
        </div>
        {loading ? <LoadingSpinner /> : <ProductCompareTable products={products} />}
      </section>

      <section className="section ai-compare-box">
        <div className="section-header">
          <h2>AI 비교 설명</h2>
        </div>
        <textarea value={criteria} onChange={(event) => setCriteria(event.target.value)} rows="3" />
        {hasMixedCategories && (
          <p className="error-text">
            서로 다른 카테고리 상품은 AI 비교 설명을 제공하지 않습니다. 같은 카테고리 상품끼리 선택해 주세요.
          </p>
        )}
        <button
          className="button primary"
          onClick={askAi}
          disabled={compareTask.status === "loading" || compareIds.length < 2 || hasMixedCategories}
          type="button"
        >
          {compareTask.status === "loading" ? "비교 설명 생성 중" : "AI 비교 설명 요청"}
        </button>
        {aiLoading && <LoadingSpinner label="AI가 비교 설명을 작성하고 있습니다" />}
        {aiError && <p className="error-text">{aiError}</p>}
        {aiAnswer && <div className="ai-result-box">{aiAnswer}</div>}
      </section>
    </div>
  );
}

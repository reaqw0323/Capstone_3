import { useEffect, useState } from "react";
import { requestAiCompare } from "../api/ai";
import { fetchCompareProducts } from "../api/products";
import LoadingSpinner from "../components/LoadingSpinner";
import ProductCompareTable from "../components/ProductCompareTable";
import { useCompare } from "../context/CompareContext";

export default function ComparePage() {
  const { compareIds, clearCompare } = useCompare();
  const [products, setProducts] = useState([]);
  const [criteria, setCriteria] = useState("가격, 스펙, 평점, 리뷰 기준으로 비교해줘");
  const [aiAnswer, setAiAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);

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
    setAiLoading(true);
    setAiAnswer("");
    try {
      const result = await requestAiCompare(compareIds, criteria);
      setAiAnswer(result.answer);
    } finally {
      setAiLoading(false);
    }
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
        <button className="button primary" onClick={askAi} disabled={aiLoading || compareIds.length < 2} type="button">
          AI 비교 설명 요청
        </button>
        {aiLoading && <LoadingSpinner label="AI가 비교 설명을 작성하고 있습니다" />}
        {aiAnswer && <pre className="ai-result">{aiAnswer}</pre>}
      </section>
    </div>
  );
}

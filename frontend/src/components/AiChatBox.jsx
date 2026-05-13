import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { requestRecommendation } from "../api/ai";
import { useCart } from "../context/CartContext";

const examples = [
  "20만 원 이하로 자취방에서 쓸 무선청소기 추천해줘",
  "부모님이 쓰기 쉬운 공기청정기 중 가성비 좋은 거 알려줘",
  "게임용 모니터인데 30만 원 안쪽으로 괜찮은 거 비교해줘",
  "리뷰 단점 적은 이어폰 추천해줘",
];

export default function AiChatBox({ initialMessage = "" }) {
  const { addToCart, sessionId } = useCart();
  const [message, setMessage] = useState(initialMessage);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setMessage(initialMessage);
  }, [initialMessage]);

  const submit = async (event) => {
    event?.preventDefault();
    const userMessage = message.trim();
    if (!userMessage) return;

    setLoading(true);
    setError("");
    setHistory((current) => [...current, { role: "user", content: userMessage }]);
    setMessage("");

    try {
      const result = await requestRecommendation(userMessage, sessionId);
      setHistory((current) => [
        ...current,
        { role: "assistant", content: result.answer, products: result.products || [] },
      ]);
    } catch {
      setError("AI 추천 요청 중 오류가 발생했습니다. 백엔드와 Ollama 상태를 확인해 주세요.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="chat-panel">
      <div className="example-row">
        {examples.map((example) => (
          <button key={example} type="button" onClick={() => setMessage(example)}>
            {example}
          </button>
        ))}
      </div>

      <div className="chat-history">
        {history.length === 0 && (
          <div className="assistant-empty">
            예산, 용도, 카테고리를 함께 말하면 DB 상품 안에서만 추천합니다.
          </div>
        )}
        {history.map((item, index) => (
          <div key={`${item.role}-${index}`} className={`chat-message ${item.role}`}>
            <div className="chat-role-label">
              {item.role === "user" ? "나" : "AI 쇼핑 도우미"}
            </div>
            <pre>{item.content}</pre>
            {item.products?.length > 0 && (
              <div className="mini-products">
                {item.products.slice(0, 4).map((product) => (
                  <div key={product.id} className="mini-product">
                    <Link to={`/products/${product.id}`} className="mini-product-link">
                      <img src={product.image_url} alt={product.name} />
                      <span>{product.name}</span>
                      <strong>{product.price.toLocaleString("ko-KR")}원</strong>
                    </Link>
                    <button className="button secondary" type="button" onClick={() => addToCart(product.id, 1)}>
                      담기
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="chat-message">
            <div className="chat-role-label">AI 쇼핑 도우미</div>
            <div className="chat-typing">
              <span /><span /><span />
            </div>
          </div>
        )}
      </div>

      {error && <p className="error-text">{error}</p>}

      <form className="chat-input-row" onSubmit={submit}>
        <input
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="예: 20만 원 이하 무선청소기 추천해줘"
        />
        <button className="button primary" disabled={loading} type="submit">
          질문하기
        </button>
      </form>
    </section>
  );
}

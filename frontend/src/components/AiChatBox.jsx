import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAiState } from "../context/AiStateContext";
import { useCart } from "../context/CartContext";

const examples = [
  "20만 원 이하로 자취방에서 쓸 무선청소기 추천해줘",
  "부모님이 쓰기 쉬운 공기청정기 중 가성비 좋은 거 알려줘",
  "게임용 모니터인데 30만 원 안쪽으로 괜찮은 거 비교해줘",
  "리뷰 단점 적은 이어폰 추천해줘",
];

export default function AiChatBox({ initialMessage = "" }) {
  const { addToCart, sessionId } = useCart();
  const { assistantHistory, assistantLoading, askAssistant, clearAssistantHistory } = useAiState();
  const [message, setMessage] = useState(initialMessage);
  const displayedHistory = assistantHistory.slice().reverse();

  useEffect(() => {
    setMessage(initialMessage);
  }, [initialMessage]);

  const submit = async (event) => {
    event?.preventDefault();
    const userMessage = message.trim();
    if (!userMessage) return;

    setMessage("");
    await askAssistant(userMessage, sessionId);
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
        {displayedHistory.length === 0 && (
          <div className="assistant-empty">
            예산, 용도, 카테고리를 함께 말하면 DB 상품 안에서만 추천합니다. 최근 답변은 5개까지 유지됩니다.
          </div>
        )}
        {displayedHistory.map((item) => (
          <div key={item.id} className="chat-thread">
            <div className="chat-message user">
              <div className="chat-role-label">나</div>
              <pre>{item.question}</pre>
            </div>

            <div className="chat-message assistant">
              <div className="chat-role-label">AI 쇼핑 도우미</div>
              {item.status === "loading" ? (
                <div className="chat-typing">
                  <span /><span /><span />
                </div>
              ) : item.status === "error" ? (
                <p className="error-text">{item.error}</p>
              ) : (
                <>
                  <pre>{item.answer}</pre>
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
                </>
              )}
            </div>
          </div>
        ))}
      </div>

      {displayedHistory.length > 0 && (
        <div className="chat-tools">
          <button className="button secondary" type="button" onClick={clearAssistantHistory} disabled={assistantLoading}>
            최근 답변 비우기
          </button>
        </div>
      )}

      <form className="chat-input-row" onSubmit={submit}>
        <input
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="예: 20만 원 이하 무선청소기 추천해줘"
        />
        <button className="button primary" disabled={assistantLoading} type="submit">
          {assistantLoading ? "답변 생성 중" : "질문하기"}
        </button>
      </form>
    </section>
  );
}

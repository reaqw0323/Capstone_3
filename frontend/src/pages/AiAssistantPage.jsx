import { useSearchParams } from "react-router-dom";
import AiChatBox from "../components/AiChatBox";

export default function AiAssistantPage() {
  const [searchParams] = useSearchParams();
  const initialMessage = searchParams.get("message") || "";

  return (
    <div className="page">
      <section className="section assistant-page">
        <div className="section-header">
          <div>
            <h1>AI 쇼핑 도우미</h1>
            <p>EasyPick DB 상품 후보 안에서만 추천과 비교 설명을 제공합니다.</p>
          </div>
        </div>
        <AiChatBox initialMessage={initialMessage} />
      </section>
    </div>
  );
}

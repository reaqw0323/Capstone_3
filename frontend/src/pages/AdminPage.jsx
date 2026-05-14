import { useEffect, useMemo, useState } from "react";
import {
  createProduct,
  deleteProduct,
  fetchAiModels,
  fetchAiSettings,
  testAiSettings,
  unloadAiModel,
  updateAiSettings,
  updateProduct,
} from "../api/admin";
import { fetchAdminOrders, updateOrderStatus } from "../api/orders";
import { fetchCategories, fetchProducts } from "../api/products";
import LoadingSpinner from "../components/LoadingSpinner";
import OrderStatusBadge from "../components/OrderStatusBadge";

const emptyForm = {
  name: "",
  brand: "",
  category_id: "",
  price: "",
  original_price: "",
  image_url: "/assets/laptop.svg",
  short_description: "",
  detail_description: "",
  recommended_for: "",
  cautions: "",
  specs: '{\n  "주요스펙": "값을 입력하세요"\n}',
  rating: "4.0",
  review_count: "0",
  stock: "10",
};

const imageOptions = [
  "/assets/laptop.svg",
  "/assets/monitor.svg",
  "/assets/vacuum.svg",
  "/assets/air-purifier.svg",
  "/assets/earphones.svg",
  "/assets/keyboard.svg",
  "/assets/mouse.svg",
  "/assets/smartwatch.svg",
];

const orderStatuses = ["주문 접수", "결제 확인", "배송 준비", "배송 중", "배송 완료", "주문 취소"];

const defaultAiSettings = {
  provider: "ollama",
  ollama_base_url: "http://ollama:11434",
  ollama_model: "easypick-ai",
  lmstudio_base_url: "http://host.docker.internal:1234/v1",
  lmstudio_model: "local-model",
  lmstudio_api_key: "",
};

function toForm(product) {
  return {
    name: product.name || "",
    brand: product.brand || "",
    category_id: String(product.category_id || ""),
    price: String(product.price || ""),
    original_price: product.original_price ? String(product.original_price) : "",
    image_url: product.image_url || "/assets/laptop.svg",
    short_description: product.short_description || "",
    detail_description: product.detail_description || "",
    recommended_for: product.recommended_for || "",
    cautions: product.cautions || "",
    specs: JSON.stringify(product.specs || {}, null, 2),
    rating: String(product.rating || "0"),
    review_count: String(product.review_count || "0"),
    stock: String(product.stock || "0"),
  };
}

function toPayload(form) {
  return {
    name: form.name.trim(),
    brand: form.brand.trim(),
    category_id: Number(form.category_id),
    price: Number(form.price),
    original_price: form.original_price === "" ? null : Number(form.original_price),
    image_url: form.image_url,
    short_description: form.short_description.trim(),
    detail_description: form.detail_description.trim(),
    recommended_for: form.recommended_for.trim(),
    cautions: form.cautions.trim(),
    specs: JSON.parse(form.specs || "{}"),
    rating: Number(form.rating),
    review_count: Number(form.review_count),
    stock: Number(form.stock),
  };
}

export default function AdminPage() {
  const [categories, setCategories] = useState([]);
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [aiSettings, setAiSettings] = useState(defaultAiSettings);
  const [aiModels, setAiModels] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [aiSaving, setAiSaving] = useState(false);
  const [aiLoadingModels, setAiLoadingModels] = useState(false);
  const [aiTesting, setAiTesting] = useState(false);
  const [aiUnloading, setAiUnloading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [aiMessage, setAiMessage] = useState("");
  const [aiError, setAiError] = useState("");

  const categoryMap = useMemo(() => {
    return Object.fromEntries(categories.map((category) => [category.id, category.name]));
  }, [categories]);

  function getAiBaseUrl(settings) {
    return settings.provider === "lmstudio"
      ? settings.lmstudio_base_url
      : settings.ollama_base_url;
  }

  function getAiModel(settings) {
    return settings.provider === "lmstudio" ? settings.lmstudio_model : settings.ollama_model;
  }

  async function loadAiModels(settingsOverride = aiSettings, options = {}) {
    const settings = { ...defaultAiSettings, ...settingsOverride };
    const silent = options.silent === true;
    setAiLoadingModels(true);
    if (!silent) {
      setAiMessage("");
    }
    setAiError("");
    setAiModels([]);
    try {
      const data = await fetchAiModels(
        settings.provider,
        getAiBaseUrl(settings),
        settings.provider === "lmstudio" ? settings.lmstudio_api_key : ""
      );
      const models = data.models || [];
      setAiModels(models);
      if (
        settings.provider === "lmstudio" &&
        models.length &&
        !models.some((model) => model.id === settings.lmstudio_model)
      ) {
        setAiSettings((current) =>
          current.provider === "lmstudio" ? { ...current, lmstudio_model: models[0].id } : current
        );
      }
      if (settings.provider === "lmstudio") {
        setAiMessage(
          models.length
            ? `LM Studio 모델 ${models.length}개를 자동으로 불러왔습니다.`
            : "LM Studio 서버는 감지됐지만 표시할 LLM 모델이 없습니다."
        );
      } else if (!silent) {
        setAiMessage(`${models.length}개 모델을 불러왔습니다.`);
      }
    } catch (err) {
      setAiModels([]);
      if (settings.provider === "lmstudio") {
        setAiError(
          "LM Studio 서버를 찾지 못했습니다. LM Studio에서 Local Server를 켠 뒤 다시 확인해 주세요."
        );
      } else if (!silent) {
        setAiError(err.message || "모델 목록을 불러오지 못했습니다.");
      }
    } finally {
      setAiLoadingModels(false);
    }
  }

  const loadData = async () => {
    setLoading(true);
    setError("");
    try {
      const [categoryData, productData, orderData] = await Promise.all([
        fetchCategories(),
        fetchProducts({ sort: "new" }),
        fetchAdminOrders(),
      ]);
      const aiData = await fetchAiSettings();
      const loadedAiSettings = { ...defaultAiSettings, ...aiData };
      setCategories(categoryData);
      setProducts(productData);
      setOrders(orderData);
      setAiSettings(loadedAiSettings);
      await loadAiModels(loadedAiSettings, { silent: loadedAiSettings.provider !== "lmstudio" });
      if (!form.category_id && categoryData[0]) {
        setForm((current) => ({ ...current, category_id: String(categoryData[0].id) }));
      }
    } catch (err) {
      setError(
        "백엔드 또는 DB에 연결하지 못했습니다. docker compose up -d 실행 후 다시 확인해 주세요."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const updateField = (key, value) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const updateAiField = (key, value) => {
    setAiSettings((current) => ({ ...current, [key]: value }));
  };

  const activeAiModel = getAiModel(aiSettings);
  const activeModelIsListed = aiModels.some((model) => model.id === activeAiModel);

  const releaseAiProvider = async (provider = aiSettings.provider, settingsOverride = aiSettings, options = {}) => {
    const silent = options.silent === true;
    const model =
      provider === "lmstudio" ? settingsOverride.lmstudio_model : settingsOverride.ollama_model;
    setAiUnloading(true);
    if (!silent) {
      setAiMessage("");
    }
    setAiError("");
    try {
      const result = await unloadAiModel(provider, model);
      if (!silent) {
        setAiMessage(
          result.ok
            ? `${provider === "lmstudio" ? "LM Studio" : "Ollama"} 모델 연결을 끊었습니다.`
            : `${provider === "lmstudio" ? "LM Studio" : "Ollama"} 모델 연결 끊기 요청을 보냈지만 이미 내려가 있거나 응답하지 않습니다.`
        );
      }
      return result;
    } catch (err) {
      if (!silent) {
        setAiError(err.message || "모델 연결 끊기에 실패했습니다.");
      }
      return { ok: false };
    } finally {
      setAiUnloading(false);
    }
  };

  const changeAiProvider = async (nextProvider) => {
    const previousSettings = aiSettings;
    const previousProvider = previousSettings.provider;
    const nextSettings = { ...aiSettings, provider: nextProvider };
    setAiSettings(nextSettings);
    setAiMessage(
      `${previousProvider === "lmstudio" ? "LM Studio" : "Ollama"} 모델 연결을 정리하는 중입니다.`
    );
    await releaseAiProvider(previousProvider, previousSettings, { silent: true });
    await loadAiModels(nextSettings, { silent: false });
  };

  const saveAiConfig = async () => {
    setAiSaving(true);
    setAiMessage("");
    setAiError("");
    try {
      const saved = await updateAiSettings(aiSettings);
      setAiSettings({ ...defaultAiSettings, ...saved });
      setAiMessage("AI 설정이 저장되었습니다.");
    } catch (err) {
      setAiError(err.message || "AI 설정 저장 중 오류가 발생했습니다.");
    } finally {
      setAiSaving(false);
    }
  };

  const testAiConfig = async () => {
    setAiTesting(true);
    setAiMessage("");
    setAiError("");
    try {
      const result = await testAiSettings(aiSettings);
      setAiMessage(`연결 테스트 성공: ${result.answer}`);
    } catch (err) {
      setAiError(err.message || "AI 연결 테스트에 실패했습니다.");
    } finally {
      setAiTesting(false);
    }
  };

  const resetForm = () => {
    setEditingId(null);
    setMessage("");
    setError("");
    setForm({
      ...emptyForm,
      category_id: categories[0] ? String(categories[0].id) : "",
    });
  };

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setMessage("");
    setError("");

    try {
      const payload = toPayload(form);
      if (!payload.name || !payload.brand || !payload.category_id || Number.isNaN(payload.price)) {
        throw new Error("상품명, 브랜드, 카테고리, 가격은 필수입니다.");
      }

      if (editingId) {
        await updateProduct(editingId, payload);
        setMessage("상품이 수정되었습니다.");
      } else {
        await createProduct(payload);
        setMessage("상품이 등록되었습니다.");
      }

      resetForm();
      await loadData();
    } catch (err) {
      setError(err.message || "저장 중 오류가 발생했습니다.");
    } finally {
      setSaving(false);
    }
  };

  const editProduct = (product) => {
    setEditingId(product.id);
    setMessage("");
    setError("");
    setForm(toForm(product));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const removeProduct = async (product) => {
    const ok = window.confirm(`${product.name} 상품을 삭제할까요?`);
    if (!ok) return;

    setSaving(true);
    setMessage("");
    setError("");
    try {
      await deleteProduct(product.id);
      setMessage("상품이 삭제되었습니다.");
      await loadData();
      if (editingId === product.id) resetForm();
    } catch (err) {
      setError(err.message || "삭제 중 오류가 발생했습니다.");
    } finally {
      setSaving(false);
    }
  };

  const changeOrderStatus = async (orderId, status) => {
    setSaving(true);
    setMessage("");
    setError("");
    try {
      await updateOrderStatus(orderId, status);
      setMessage("주문 상태가 변경되었습니다.");
      await loadData();
    } catch (err) {
      setError(err.message || "주문 상태 변경 중 오류가 발생했습니다.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page">
      <section className="section">
        <div className="section-header">
          <div>
            <h1>관리자 상품 관리</h1>
            <p>시연용 상품을 직접 등록, 수정, 삭제할 수 있습니다.</p>
          </div>
          <button className="button secondary" type="button" onClick={loadData}>
            새로고침
          </button>
        </div>

        {loading && <LoadingSpinner label="관리자 데이터를 불러오는 중입니다" />}
        {message && <p className="success-text">{message}</p>}
        {error && <p className="error-text">{error}</p>}
      </section>

      <section className="section">
        <div className="section-header">
          <div>
            <h2>AI 연결 설정</h2>
            <p>Ollama와 LM Studio 중 사용할 로컬 AI 서버를 선택합니다.</p>
          </div>
          <span className="ai-status-pill">
            {aiSettings.provider === "lmstudio" ? "LM Studio" : "Ollama"} · {activeAiModel}
          </span>
        </div>

        {aiMessage && <p className="success-text">{aiMessage}</p>}
        {aiError && <p className="error-text">{aiError}</p>}

        <div className="admin-form ai-settings-form">
          <label>
            AI 서버
            <select
              value={aiSettings.provider}
              onChange={(event) => {
                changeAiProvider(event.target.value);
              }}
              disabled={aiUnloading}
            >
              <option value="ollama">Ollama</option>
              <option value="lmstudio">LM Studio</option>
            </select>
          </label>

          {aiSettings.provider === "ollama" ? (
            <>
              <label>
                Ollama 주소
                <input
                  value={aiSettings.ollama_base_url}
                  onChange={(event) => updateAiField("ollama_base_url", event.target.value)}
                  placeholder="http://ollama:11434"
                />
              </label>
              <label>
                Ollama 모델
                {aiModels.length ? (
                  <select
                    value={aiSettings.ollama_model}
                    onChange={(event) => updateAiField("ollama_model", event.target.value)}
                  >
                    {!activeModelIsListed && (
                      <option value={aiSettings.ollama_model}>{aiSettings.ollama_model}</option>
                    )}
                    {aiModels.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    value={aiSettings.ollama_model}
                    onChange={(event) => updateAiField("ollama_model", event.target.value)}
                    placeholder="easypick-ai"
                  />
                )}
              </label>
            </>
          ) : (
            <>
              <label>
                LM Studio 주소
                <input
                  value={aiSettings.lmstudio_base_url}
                  onChange={(event) => updateAiField("lmstudio_base_url", event.target.value)}
                  placeholder="http://host.docker.internal:1234/v1"
                />
              </label>
              <label>
                LM Studio 모델
                {aiModels.length ? (
                  <select
                    value={aiSettings.lmstudio_model}
                    onChange={(event) => updateAiField("lmstudio_model", event.target.value)}
                  >
                    {!activeModelIsListed && (
                      <option value={aiSettings.lmstudio_model}>{aiSettings.lmstudio_model}</option>
                    )}
                    {aiModels.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    value={aiSettings.lmstudio_model}
                    onChange={(event) => updateAiField("lmstudio_model", event.target.value)}
                    placeholder="LM Studio 모델을 자동으로 불러옵니다"
                  />
                )}
              </label>
              <label className="admin-form-wide">
                LM Studio API 키
                <input
                  value={aiSettings.lmstudio_api_key || ""}
                  onChange={(event) => updateAiField("lmstudio_api_key", event.target.value)}
                  placeholder="토큰을 설정하지 않았다면 비워두세요"
                />
              </label>
            </>
          )}

          <div className="admin-actions">
            <button
              className="button secondary"
              type="button"
              onClick={() => loadAiModels(aiSettings, { silent: false })}
              disabled={aiLoadingModels}
            >
              {aiLoadingModels ? "불러오는 중" : "모델 새로고침"}
            </button>
            <button className="button secondary" type="button" onClick={testAiConfig} disabled={aiTesting}>
              {aiTesting ? "테스트 중" : "연결 테스트"}
            </button>
            <button
              className="button secondary"
              type="button"
              onClick={() => releaseAiProvider(aiSettings.provider, aiSettings, { silent: false })}
              disabled={aiUnloading}
            >
              {aiUnloading ? "정리 중" : "현재 모델 연결 끊기"}
            </button>
            <button className="button primary" type="button" onClick={saveAiConfig} disabled={aiSaving}>
              {aiSaving ? "저장 중" : "AI 설정 저장"}
            </button>
          </div>

          {!!aiModels.length && (
            <div className="admin-form-wide ai-model-list">
              {aiModels.map((model) => (
                <button
                  key={model.id}
                  type="button"
                  className={model.id === activeAiModel ? "ai-model-option active" : "ai-model-option"}
                  onClick={() =>
                    updateAiField(
                      aiSettings.provider === "lmstudio" ? "lmstudio_model" : "ollama_model",
                      model.id
                    )
                  }
                >
                  <strong>{model.name}</strong>
                  <small>
                    {model.id}
                    {model.state ? ` · ${model.state}` : ""}
                    {model.details?.quantization ? ` · ${model.details.quantization}` : ""}
                  </small>
                </button>
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="section">
        <div className="section-header">
          <div>
            <h2>상품 등록</h2>
            <p>시연용 상품을 직접 등록, 수정, 삭제할 수 있습니다.</p>
          </div>
        </div>

        <form className="admin-form" onSubmit={submit}>
          {editingId && (
            <div className="editing-banner">
              ✏️ 수정 모드 — ID {editingId} 상품을 수정하고 있습니다. 취소하려면 [새 상품 입력]을 누르세요.
            </div>
          )}
          <label>
            상품명 <span className="required-mark">*</span>
            <input required value={form.name} onChange={(event) => updateField("name", event.target.value)} placeholder="예: 다이슨 V15 무선청소기" />
          </label>
          <label>
            브랜드 <span className="required-mark">*</span>
            <input required value={form.brand} onChange={(event) => updateField("brand", event.target.value)} placeholder="예: 다이슨" />
          </label>
          <label>
            카테고리 <span className="required-mark">*</span>
            <select
              required
              value={form.category_id}
              onChange={(event) => updateField("category_id", event.target.value)}
            >
              <option value="">선택하세요</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            판매가 <span className="required-mark">*</span>
            <input
              required
              type="number"
              min="0"
              value={form.price}
              onChange={(event) => updateField("price", event.target.value)}
              placeholder="예: 159000"
            />
          </label>
          <label>
            정가 <span style={{ color: "var(--muted)", fontWeight: 400 }}>(선택)</span>
            <input
              type="number"
              min="0"
              value={form.original_price}
              onChange={(event) => updateField("original_price", event.target.value)}
              placeholder="할인 전 가격"
            />
          </label>
          <label>
            이미지
            <div className="admin-image-select-row">
              <select value={form.image_url} onChange={(event) => updateField("image_url", event.target.value)}>
                {imageOptions.map((image) => (
                  <option key={image} value={image}>
                    {image}
                  </option>
                ))}
              </select>
              <img src={form.image_url} alt="미리보기" className="admin-image-preview" />
            </div>
          </label>
          <label>
            평점
            <input
              type="number"
              min="0"
              max="5"
              step="0.1"
              value={form.rating}
              onChange={(event) => updateField("rating", event.target.value)}
              placeholder="0.0 ~ 5.0"
            />
          </label>
          <label>
            리뷰 수
            <input
              type="number"
              min="0"
              value={form.review_count}
              onChange={(event) => updateField("review_count", event.target.value)}
              placeholder="0"
            />
          </label>
          <label>
            재고
            <input
              type="number"
              min="0"
              value={form.stock}
              onChange={(event) => updateField("stock", event.target.value)}
              placeholder="0"
            />
          </label>
          <label className="admin-form-wide">
            짧은 설명
            <input
              value={form.short_description}
              onChange={(event) => updateField("short_description", event.target.value)}
              placeholder="상품의 핵심 특징을 한 줄로 입력하세요"
            />
          </label>
          <label className="admin-form-wide">
            상세설명
            <textarea
              rows="4"
              value={form.detail_description}
              onChange={(event) => updateField("detail_description", event.target.value)}
              placeholder="상세 페이지와 AI 답변에 활용할 상품 설명을 입력하세요"
            />
          </label>
          <label>
            추천대상
            <textarea
              rows="4"
              value={form.recommended_for}
              onChange={(event) => updateField("recommended_for", event.target.value)}
              placeholder="예: 자취생, 사무용 사용자, 부모님 선물"
            />
          </label>
          <label>
            주의사항
            <textarea
              rows="4"
              value={form.cautions}
              onChange={(event) => updateField("cautions", event.target.value)}
              placeholder="예: 고사양 게임에는 부족할 수 있음"
            />
          </label>
          <label className="admin-form-wide">
            주요 스펙 JSON
            <textarea
              rows="8"
              value={form.specs}
              onChange={(event) => updateField("specs", event.target.value)}
            />
          </label>
          <div className="admin-actions">
            <button className="button primary" type="submit" disabled={saving}>
              {editingId ? "상품 수정" : "상품 등록"}
            </button>
            <button className="button secondary" type="button" onClick={resetForm}>
              새 상품 입력
            </button>
          </div>
        </form>
      </section>

      <section className="section">
        <div className="section-header">
          <div>
            <h2>등록된 상품</h2>
            <p>{products.length}개 상품</p>
          </div>
        </div>

        <div className="table-scroll">
          <table className="admin-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>상품</th>
                <th>카테고리</th>
                <th>가격</th>
                <th>평점</th>
                <th>재고</th>
                <th>관리</th>
              </tr>
            </thead>
            <tbody>
              {products.map((product) => (
                <tr key={product.id}>
                  <td>{product.id}</td>
                  <td>
                    <div className="admin-product-cell">
                      <img src={product.image_url} alt={product.name} />
                      <span>
                        <strong>{product.name}</strong>
                        <small>{product.brand}</small>
                      </span>
                    </div>
                  </td>
                  <td>{categoryMap[product.category_id] || product.category}</td>
                  <td>{product.price.toLocaleString("ko-KR")}원</td>
                  <td>{product.rating}</td>
                  <td>{product.stock}</td>
                  <td>
                    <div className="admin-row-actions">
                      <button className="button secondary" type="button" onClick={() => editProduct(product)}>
                        수정
                      </button>
                      <button className="button danger" type="button" onClick={() => removeProduct(product)}>
                        삭제
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!products.length && (
                <tr>
                  <td colSpan="7">등록된 상품이 없습니다.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="section">
        <div className="section-header">
          <div>
            <h2>주문 관리</h2>
            <p>{orders.length}개 주문</p>
          </div>
        </div>

        <div className="table-scroll">
          <table className="admin-table">
            <thead>
              <tr>
                <th>주문번호</th>
                <th>주문자</th>
                <th>결제 방식</th>
                <th>총 금액</th>
                <th>상태</th>
                <th>주문일</th>
                <th>상태 변경</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.id}>
                  <td>{order.order_number}</td>
                  <td>
                    <strong>{order.customer_name}</strong>
                    <small className="admin-subtext">{order.phone}</small>
                  </td>
                  <td>{order.payment_method}</td>
                  <td>{order.total_price.toLocaleString("ko-KR")}원</td>
                  <td><OrderStatusBadge status={order.status} /></td>
                  <td>{new Date(order.created_at).toLocaleString("ko-KR")}</td>
                  <td>
                    <select
                      value={order.status}
                      disabled={saving}
                      onChange={(event) => changeOrderStatus(order.id, event.target.value)}
                    >
                      {orderStatuses.map((status) => (
                        <option key={status} value={status}>
                          {status}
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
              {!orders.length && (
                <tr>
                  <td colSpan="7">아직 주문이 없습니다.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

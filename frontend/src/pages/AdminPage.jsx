import { useEffect, useMemo, useState } from "react";
import { createProduct, deleteProduct, updateProduct } from "../api/admin";
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

function toForm(product) {
  return {
    name: product.name || "",
    brand: product.brand || "",
    category_id: String(product.category_id || ""),
    price: String(product.price || ""),
    original_price: product.original_price ? String(product.original_price) : "",
    image_url: product.image_url || "/assets/laptop.svg",
    short_description: product.short_description || "",
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
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const categoryMap = useMemo(() => {
    return Object.fromEntries(categories.map((category) => [category.id, category.name]));
  }, [categories]);

  const loadData = async () => {
    setLoading(true);
    setError("");
    try {
      const [categoryData, productData, orderData] = await Promise.all([
        fetchCategories(),
        fetchProducts({ sort: "new" }),
        fetchAdminOrders(),
      ]);
      setCategories(categoryData);
      setProducts(productData);
      setOrders(orderData);
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

        <form className="admin-form" onSubmit={submit}>
          <label>
            상품명
            <input value={form.name} onChange={(event) => updateField("name", event.target.value)} />
          </label>
          <label>
            브랜드
            <input value={form.brand} onChange={(event) => updateField("brand", event.target.value)} />
          </label>
          <label>
            카테고리
            <select
              value={form.category_id}
              onChange={(event) => updateField("category_id", event.target.value)}
            >
              <option value="">선택</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            판매가
            <input
              type="number"
              min="0"
              value={form.price}
              onChange={(event) => updateField("price", event.target.value)}
            />
          </label>
          <label>
            정가
            <input
              type="number"
              min="0"
              value={form.original_price}
              onChange={(event) => updateField("original_price", event.target.value)}
            />
          </label>
          <label>
            이미지
            <select value={form.image_url} onChange={(event) => updateField("image_url", event.target.value)}>
              {imageOptions.map((image) => (
                <option key={image} value={image}>
                  {image}
                </option>
              ))}
            </select>
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
            />
          </label>
          <label>
            리뷰 수
            <input
              type="number"
              min="0"
              value={form.review_count}
              onChange={(event) => updateField("review_count", event.target.value)}
            />
          </label>
          <label>
            재고
            <input
              type="number"
              min="0"
              value={form.stock}
              onChange={(event) => updateField("stock", event.target.value)}
            />
          </label>
          <label className="admin-form-wide">
            짧은 설명
            <input
              value={form.short_description}
              onChange={(event) => updateField("short_description", event.target.value)}
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

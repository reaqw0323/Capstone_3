import { Link, NavLink, Route, Routes } from "react-router-dom";
import { useCart } from "./context/CartContext";
import { useCompare } from "./context/CompareContext";
import AdminPage from "./pages/AdminPage";
import AiAssistantPage from "./pages/AiAssistantPage";
import CartPage from "./pages/CartPage";
import ComparePage from "./pages/ComparePage";
import CheckoutPage from "./pages/CheckoutPage";
import HomePage from "./pages/HomePage";
import OrderDetailPage from "./pages/OrderDetailPage";
import OrdersPage from "./pages/OrdersPage";
import ProductDetailPage from "./pages/ProductDetailPage";
import ProductListPage from "./pages/ProductListPage";

export default function App() {
  const { compareIds } = useCompare();
  const { cart } = useCart();

  return (
    <div className="app-shell">
      <header className="topbar">
        <Link className="brand" to="/">
          <span className="brand-mark">E</span>
          <span>
            <strong>EasyPick AI</strong>
            <small>로컬 AI 쇼핑 도우미</small>
          </span>
        </Link>
        <nav className="nav">
          <NavLink to="/products">상품</NavLink>
          <NavLink to="/cart">장바구니 {cart.total_quantity > 0 && `(${cart.total_quantity})`}</NavLink>
          <NavLink to="/compare">비교 {compareIds.length > 0 && `(${compareIds.length})`}</NavLink>
          <NavLink to="/orders">주문내역</NavLink>
          <NavLink to="/ai">AI 도우미</NavLink>
          <NavLink to="/admin">관리자</NavLink>
        </nav>
      </header>

      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/products" element={<ProductListPage />} />
          <Route path="/products/:id" element={<ProductDetailPage />} />
          <Route path="/cart" element={<CartPage />} />
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/orders" element={<OrdersPage />} />
          <Route path="/orders/:orderNumber" element={<OrderDetailPage />} />
          <Route path="/compare" element={<ComparePage />} />
          <Route path="/ai" element={<AiAssistantPage />} />
          <Route path="/admin" element={<AdminPage />} />
        </Routes>
      </main>
    </div>
  );
}

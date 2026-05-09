import { createContext, useContext, useEffect, useMemo, useState } from "react";
import {
  addCartItem,
  clearCart as clearCartApi,
  fetchCart,
  removeCartItem,
  updateCartItem,
} from "../api/cart";
import { getSessionId } from "../utils/session";

const CartContext = createContext(null);

const emptyCart = {
  items: [],
  total_price: 0,
  total_quantity: 0,
};

export function CartProvider({ children }) {
  const [sessionId] = useState(() => getSessionId());
  const [cart, setCart] = useState(emptyCart);
  const [loading, setLoading] = useState(false);
  const [lastMessage, setLastMessage] = useState("");

  const refreshCart = async () => {
    setLoading(true);
    try {
      const next = await fetchCart(sessionId);
      setCart(next);
      return next;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshCart().catch(() => {
      setCart(emptyCart);
    });
  }, []);

  const value = useMemo(() => {
    const addToCart = async (productId, quantity = 1) => {
      const next = await addCartItem(sessionId, productId, quantity);
      setCart(next);
      setLastMessage("장바구니에 담았습니다.");
      return next;
    };

    const changeQuantity = async (cartItemId, quantity) => {
      const next = await updateCartItem(sessionId, cartItemId, quantity);
      setCart(next);
      return next;
    };

    const removeFromCart = async (cartItemId) => {
      const next = await removeCartItem(sessionId, cartItemId);
      setCart(next);
      return next;
    };

    const clearCart = async () => {
      const next = await clearCartApi(sessionId);
      setCart(next);
      return next;
    };

    return {
      sessionId,
      cart,
      loading,
      lastMessage,
      setLastMessage,
      refreshCart,
      addToCart,
      changeQuantity,
      removeFromCart,
      clearCart,
    };
  }, [sessionId, cart, loading, lastMessage]);

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error("useCart는 CartProvider 안에서 사용해야 합니다.");
  }
  return context;
}

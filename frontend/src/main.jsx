import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import { AiStateProvider } from "./context/AiStateContext.jsx";
import { CartProvider } from "./context/CartContext.jsx";
import { CompareProvider } from "./context/CompareContext.jsx";
import "./styles.css";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <CompareProvider>
        <CartProvider>
          <AiStateProvider>
            <App />
          </AiStateProvider>
        </CartProvider>
      </CompareProvider>
    </BrowserRouter>
  </React.StrictMode>
);

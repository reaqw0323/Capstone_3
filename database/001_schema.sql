CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS schema_migrations (
  version VARCHAR(120) PRIMARY KEY,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS categories (
  id SERIAL PRIMARY KEY,
  name VARCHAR(80) NOT NULL UNIQUE,
  description TEXT
);

CREATE TABLE IF NOT EXISTS shopping_sessions (
  id BIGSERIAL PRIMARY KEY,
  session_id VARCHAR(120) NOT NULL UNIQUE,
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (status IN ('active', 'converted', 'expired'))
);

CREATE TABLE IF NOT EXISTS products (
  id SERIAL PRIMARY KEY,
  name VARCHAR(160) NOT NULL,
  brand VARCHAR(80) NOT NULL,
  category_id INTEGER NOT NULL REFERENCES categories(id),
  price INTEGER NOT NULL CHECK (price >= 0),
  original_price INTEGER CHECK (original_price >= 0),
  image_url TEXT NOT NULL,
  short_description TEXT,
  detail_description TEXT NOT NULL DEFAULT '',
  recommended_for TEXT NOT NULL DEFAULT '',
  cautions TEXT NOT NULL DEFAULT '',
  specs JSONB NOT NULL DEFAULT '{}'::jsonb,
  rating NUMERIC(2,1) NOT NULL DEFAULT 0 CHECK (rating >= 0 AND rating <= 5),
  review_count INTEGER NOT NULL DEFAULT 0 CHECK (review_count >= 0),
  stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reviews (
  id SERIAL PRIMARY KEY,
  product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  user_name VARCHAR(60) NOT NULL,
  rating NUMERIC(2,1) NOT NULL CHECK (rating >= 0 AND rating <= 5),
  content TEXT NOT NULL,
  pros TEXT,
  cons TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cart_items (
  id SERIAL PRIMARY KEY,
  session_id VARCHAR(120) NOT NULL REFERENCES shopping_sessions(session_id) ON DELETE CASCADE,
  product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (session_id, product_id)
);

CREATE TABLE IF NOT EXISTS orders (
  id SERIAL PRIMARY KEY,
  order_number VARCHAR(40) NOT NULL UNIQUE,
  session_id VARCHAR(120) NOT NULL REFERENCES shopping_sessions(session_id) ON DELETE RESTRICT,
  customer_name VARCHAR(80) NOT NULL,
  phone VARCHAR(40) NOT NULL,
  address TEXT NOT NULL,
  delivery_memo TEXT,
  payment_method VARCHAR(40) NOT NULL,
  total_price INTEGER NOT NULL CHECK (total_price >= 0),
  status VARCHAR(30) NOT NULL DEFAULT '주문 접수',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (status IN ('주문 접수', '결제 확인', '배송 준비', '배송 중', '배송 완료', '주문 취소'))
);

CREATE TABLE IF NOT EXISTS order_items (
  id SERIAL PRIMARY KEY,
  order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
  product_name VARCHAR(160) NOT NULL,
  brand VARCHAR(80) NOT NULL,
  image_url TEXT NOT NULL,
  price INTEGER NOT NULL CHECK (price >= 0),
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  subtotal INTEGER NOT NULL CHECK (subtotal >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS order_status_history (
  id BIGSERIAL PRIMARY KEY,
  order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  previous_status VARCHAR(30),
  new_status VARCHAR(30) NOT NULL,
  changed_by VARCHAR(60) NOT NULL DEFAULT 'system',
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS inventory_transactions (
  id BIGSERIAL PRIMARY KEY,
  product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
  order_id INTEGER REFERENCES orders(id) ON DELETE SET NULL,
  reason VARCHAR(40) NOT NULL,
  quantity_change INTEGER NOT NULL CHECK (quantity_change <> 0),
  stock_after INTEGER NOT NULL CHECK (stock_after >= 0),
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (reason IN ('order_placed', 'order_cancelled', 'manual_adjustment', 'restock'))
);

CREATE TABLE IF NOT EXISTS ai_logs (
  id SERIAL PRIMARY KEY,
  session_id VARCHAR(120),
  request_type VARCHAR(30) NOT NULL DEFAULT 'general',
  user_message TEXT NOT NULL,
  ai_response TEXT NOT NULL,
  product_ids INTEGER[] DEFAULT '{}'::integer[],
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_settings (
  id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  provider VARCHAR(30) NOT NULL DEFAULT 'ollama',
  ollama_base_url TEXT NOT NULL DEFAULT 'http://ollama:11434',
  ollama_model TEXT NOT NULL DEFAULT 'easypick-ai',
  lmstudio_base_url TEXT NOT NULL DEFAULT 'http://host.docker.internal:1234/v1',
  lmstudio_model TEXT NOT NULL DEFAULT 'local-model',
  lmstudio_api_key TEXT NOT NULL DEFAULT '',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);
CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand);
CREATE INDEX IF NOT EXISTS idx_reviews_product ON reviews(product_id);
CREATE INDEX IF NOT EXISTS idx_cart_session ON cart_items(session_id);
CREATE INDEX IF NOT EXISTS idx_orders_session ON orders(session_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_status_history_order ON order_status_history(order_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_inventory_transactions_product ON inventory_transactions(product_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_inventory_transactions_order ON inventory_transactions(order_id);
CREATE INDEX IF NOT EXISTS idx_ai_logs_session ON ai_logs(session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON shopping_sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_last_seen ON shopping_sessions(last_seen_at DESC);

CREATE INDEX IF NOT EXISTS idx_products_name_trgm ON products USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_products_brand_trgm ON products USING gin (brand gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_products_short_description_trgm ON products USING gin (short_description gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_products_specs_text_trgm ON products USING gin ((specs::text) gin_trgm_ops);

DROP TRIGGER IF EXISTS set_products_updated_at ON products;
CREATE TRIGGER set_products_updated_at
BEFORE UPDATE ON products
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS set_orders_updated_at ON orders;
CREATE TRIGGER set_orders_updated_at
BEFORE UPDATE ON orders
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS set_ai_settings_updated_at ON ai_settings;
CREATE TRIGGER set_ai_settings_updated_at
BEFORE UPDATE ON ai_settings
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS set_shopping_sessions_updated_at ON shopping_sessions;
CREATE TRIGGER set_shopping_sessions_updated_at
BEFORE UPDATE ON shopping_sessions
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

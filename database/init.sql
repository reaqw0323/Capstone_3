DROP TABLE IF EXISTS ai_logs;
DROP TABLE IF EXISTS ai_settings;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS cart_items;
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS categories;

CREATE TABLE categories (
  id SERIAL PRIMARY KEY,
  name VARCHAR(80) NOT NULL UNIQUE,
  description TEXT
);

CREATE TABLE products (
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
  rating NUMERIC(2,1) NOT NULL DEFAULT 0,
  review_count INTEGER NOT NULL DEFAULT 0,
  stock INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE reviews (
  id SERIAL PRIMARY KEY,
  product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  user_name VARCHAR(60) NOT NULL,
  rating NUMERIC(2,1) NOT NULL CHECK (rating >= 0 AND rating <= 5),
  content TEXT NOT NULL,
  pros TEXT,
  cons TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE cart_items (
  id SERIAL PRIMARY KEY,
  session_id VARCHAR(120) NOT NULL,
  product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  quantity INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (session_id, product_id)
);

CREATE TABLE orders (
  id SERIAL PRIMARY KEY,
  order_number VARCHAR(40) NOT NULL UNIQUE,
  session_id VARCHAR(120) NOT NULL,
  customer_name VARCHAR(80) NOT NULL,
  phone VARCHAR(40) NOT NULL,
  address TEXT NOT NULL,
  delivery_memo TEXT,
  payment_method VARCHAR(40) NOT NULL,
  total_price INTEGER NOT NULL CHECK (total_price >= 0),
  status VARCHAR(30) NOT NULL DEFAULT '주문 접수',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE order_items (
  id SERIAL PRIMARY KEY,
  order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
  product_name VARCHAR(160) NOT NULL,
  brand VARCHAR(80) NOT NULL,
  image_url TEXT NOT NULL,
  price INTEGER NOT NULL CHECK (price >= 0),
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  subtotal INTEGER NOT NULL CHECK (subtotal >= 0)
);

CREATE TABLE ai_logs (
  id SERIAL PRIMARY KEY,
  user_message TEXT NOT NULL,
  ai_response TEXT NOT NULL,
  product_ids INTEGER[] DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE ai_settings (
  id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  provider VARCHAR(30) NOT NULL DEFAULT 'ollama',
  ollama_base_url TEXT NOT NULL DEFAULT 'http://ollama:11434',
  ollama_model TEXT NOT NULL DEFAULT 'easypick-ai',
  lmstudio_base_url TEXT NOT NULL DEFAULT 'http://host.docker.internal:1234/v1',
  lmstudio_model TEXT NOT NULL DEFAULT 'local-model',
  lmstudio_api_key TEXT NOT NULL DEFAULT '',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO ai_settings (
  id, provider, ollama_base_url, ollama_model,
  lmstudio_base_url, lmstudio_model, lmstudio_api_key
) VALUES (
  1, 'ollama', 'http://ollama:11434', 'easypick-ai',
  'http://host.docker.internal:1234/v1', 'local-model', ''
);

CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_price ON products(price);
CREATE INDEX idx_products_brand ON products(brand);
CREATE INDEX idx_reviews_product ON reviews(product_id);
CREATE INDEX idx_cart_session ON cart_items(session_id);
CREATE INDEX idx_orders_session ON orders(session_id);
CREATE INDEX idx_order_items_order ON order_items(order_id);

INSERT INTO categories (id, name, description) VALUES
(1, '노트북', '수업, 업무, 코딩, 휴대용 작업에 맞춘 노트북'),
(2, '모니터', '게임, 사무, 영상 감상용 모니터'),
(3, '무선청소기', '자취방과 가정에서 쓰기 쉬운 무선 청소기'),
(4, '공기청정기', '방, 거실, 부모님 댁에 맞춘 공기청정기'),
(5, '이어폰', '통학, 운동, 통화용 무선 이어폰'),
(6, '키보드', '사무, 코딩, 게임용 키보드'),
(7, '마우스', '사무, 게임, 휴대용 마우스'),
(8, '스마트워치', '건강 관리와 알림 확인용 스마트워치');

INSERT INTO products (id, name, brand, category_id, price, original_price, image_url, short_description, specs, rating, review_count, stock) VALUES
(1, 'LiteBook Air 14', 'NovaTech', 1, 699000, 799000, '/assets/laptop.svg', '가벼운 수업용 14인치 노트북', '{"CPU":"Ryzen 5 7530U","RAM":"16GB","Storage":"512GB SSD","Display":"14인치 FHD","Weight":"1.25kg"}', 4.5, 128, 17),
(2, 'StudyMate 15', 'Hanbit', 1, 529000, 599000, '/assets/laptop.svg', '문서 작업과 온라인 강의에 맞춘 실속형 노트북', '{"CPU":"Intel i5-1235U","RAM":"8GB","Storage":"256GB SSD","Display":"15.6인치 FHD","Weight":"1.65kg"}', 4.2, 96, 25),
(3, 'CreatorBook Pro 16', 'PixelWorks', 1, 1299000, 1499000, '/assets/laptop.svg', '영상 편집과 디자인 과제용 고성능 노트북', '{"CPU":"Intel i7-13620H","GPU":"RTX 4050","RAM":"16GB","Storage":"1TB SSD","Display":"16인치 QHD"}', 4.6, 74, 9),
(4, 'Campus Slim 13', 'Eon', 1, 849000, 929000, '/assets/laptop.svg', '휴대성과 배터리를 중시한 슬림 노트북', '{"CPU":"Ryzen 7 7730U","RAM":"16GB","Storage":"512GB SSD","Display":"13.3인치 FHD","Battery":"최대 13시간"}', 4.4, 83, 14),
(5, 'GameCore 15 RTX', 'Aster', 1, 1599000, 1799000, '/assets/laptop.svg', '게임과 그래픽 작업을 위한 게이밍 노트북', '{"CPU":"Intel i7-13700H","GPU":"RTX 4060","RAM":"16GB","Storage":"1TB SSD","RefreshRate":"144Hz"}', 4.7, 67, 8),

(6, 'ViewMax 27Q', 'NovaView', 2, 289000, 349000, '/assets/monitor.svg', '게임과 작업을 함께 쓰기 좋은 QHD 모니터', '{"Size":"27인치","Resolution":"QHD","RefreshRate":"165Hz","Panel":"IPS","Ports":"HDMI, DP"}', 4.6, 152, 30),
(7, 'OfficeClear 24', 'Hanbit', 2, 139000, 169000, '/assets/monitor.svg', '사무실과 자취방 책상에 맞는 FHD 모니터', '{"Size":"24인치","Resolution":"FHD","RefreshRate":"75Hz","Panel":"IPS","Stand":"틸트"}', 4.2, 188, 42),
(8, 'WideDesk 34', 'PixelWorks', 2, 459000, 529000, '/assets/monitor.svg', '넓은 작업 공간을 제공하는 울트라와이드 모니터', '{"Size":"34인치","Resolution":"UWQHD","RefreshRate":"100Hz","Panel":"VA","Ratio":"21:9"}', 4.5, 77, 16),
(9, 'ColorPro 27U', 'Eon', 2, 549000, 629000, '/assets/monitor.svg', '사진과 영상 확인에 좋은 4K 모니터', '{"Size":"27인치","Resolution":"4K UHD","RefreshRate":"60Hz","Panel":"IPS","Color":"sRGB 99%"}', 4.4, 64, 11),
(10, 'GameRush 25F', 'Aster', 2, 239000, 279000, '/assets/monitor.svg', '빠른 반응 속도 중심의 게이밍 모니터', '{"Size":"25인치","Resolution":"FHD","RefreshRate":"240Hz","Panel":"IPS","Response":"1ms"}', 4.3, 91, 22),

(11, 'CleanJet Mini', 'HomePure', 3, 159000, 199000, '/assets/vacuum.svg', '자취방에서 쓰기 좋은 가벼운 무선청소기', '{"Suction":"150AW","Runtime":"35분","Weight":"1.6kg","Dustbin":"0.5L","Filter":"HEPA"}', 4.4, 211, 34),
(12, 'DustZero Slim', 'Cleania', 3, 189000, 229000, '/assets/vacuum.svg', '좁은 공간 보관이 쉬운 슬림 무선청소기', '{"Suction":"170AW","Runtime":"40분","Weight":"1.8kg","Dustbin":"0.6L","Filter":"마이크로 필터"}', 4.3, 173, 27),
(13, 'PowerStick 220', 'AeroHome', 3, 249000, 299000, '/assets/vacuum.svg', '흡입력을 강화한 가정용 무선청소기', '{"Suction":"220AW","Runtime":"50분","Weight":"2.2kg","Dustbin":"0.7L","Accessories":"틈새 브러시"}', 4.6, 119, 18),
(14, 'QuietClean Lite', 'Mellow', 3, 129000, 159000, '/assets/vacuum.svg', '소음 부담이 적은 입문형 무선청소기', '{"Suction":"120AW","Runtime":"30분","Weight":"1.5kg","Noise":"68dB","Dustbin":"0.45L"}', 4.1, 142, 39),
(15, 'PetCare Stick', 'HomePure', 3, 219000, 269000, '/assets/vacuum.svg', '머리카락과 반려동물 털 청소에 초점을 둔 모델', '{"Suction":"190AW","Runtime":"45분","Weight":"2.0kg","Brush":"엉킴 방지 브러시","Filter":"HEPA"}', 4.5, 88, 15),

(16, 'AirCalm 20', 'HomePure', 4, 179000, 219000, '/assets/air-purifier.svg', '원룸과 작은 방에 맞는 공기청정기', '{"Coverage":"20m2","Filter":"H13 HEPA","Noise":"22dB","Sensor":"PM2.5","Mode":"취침 모드"}', 4.4, 168, 28),
(17, 'PureRoom 35', 'Cleania', 4, 269000, 329000, '/assets/air-purifier.svg', '안방과 거실 일부를 커버하는 중형 공기청정기', '{"Coverage":"35m2","Filter":"H13 HEPA","Noise":"24dB","Sensor":"먼지, 냄새","Display":"공기질 표시"}', 4.6, 132, 20),
(18, 'ParentCare Air', 'Mellow', 4, 239000, 289000, '/assets/air-purifier.svg', '버튼이 단순해 부모님이 쓰기 쉬운 공기청정기', '{"Coverage":"30m2","Filter":"H13 HEPA","Noise":"23dB","Controls":"큰 버튼","Mode":"자동 운전"}', 4.5, 105, 23),
(19, 'AirTower 50', 'AeroHome', 4, 399000, 469000, '/assets/air-purifier.svg', '거실용 대면적 공기청정기', '{"Coverage":"50m2","Filter":"탈취+HEPA","Noise":"28dB","Sensor":"PM1.0","Mode":"터보"}', 4.7, 84, 12),
(20, 'DeskAir Compact', 'Eon', 4, 99000, 129000, '/assets/air-purifier.svg', '책상 위에 두기 좋은 소형 공기청정기', '{"Coverage":"12m2","Filter":"복합 필터","Noise":"25dB","Power":"USB-C","Weight":"0.9kg"}', 4.0, 76, 45),

(21, 'SoundBuds Fit', 'NovaSound', 5, 79000, 99000, '/assets/earphones.svg', '운동과 통학에 쓰기 좋은 무선 이어폰', '{"ANC":"없음","Battery":"28시간","Waterproof":"IPX5","Codec":"AAC","Weight":"4.2g"}', 4.2, 240, 55),
(22, 'QuietPods ANC', 'Mellow', 5, 149000, 189000, '/assets/earphones.svg', '노이즈 캔슬링이 있는 가성비 이어폰', '{"ANC":"지원","Battery":"32시간","Waterproof":"IPX4","Codec":"AAC, SBC","Mode":"주변음"}', 4.5, 198, 37),
(23, 'CallClear Pro', 'Hanbit', 5, 119000, 149000, '/assets/earphones.svg', '통화 품질을 중시한 무선 이어폰', '{"ANC":"통화 소음 감소","Battery":"30시간","Mic":"6마이크","Waterproof":"IPX4","Codec":"AAC"}', 4.3, 116, 29),
(24, 'BassRun TWS', 'Aster', 5, 89000, 119000, '/assets/earphones.svg', '저음이 강한 음악 감상용 이어폰', '{"ANC":"없음","Battery":"26시간","Waterproof":"IPX5","Sound":"저음 강화","Latency":"게임 모드"}', 4.1, 91, 32),
(25, 'StudioBuds Lite', 'PixelWorks', 5, 199000, 239000, '/assets/earphones.svg', '균형 잡힌 음색의 프리미엄 이어폰', '{"ANC":"지원","Battery":"34시간","Waterproof":"IPX4","Codec":"LDAC","Mode":"멀티포인트"}', 4.6, 72, 18),

(26, 'KeyFlow Office', 'Hanbit', 6, 59000, 79000, '/assets/keyboard.svg', '조용한 사무용 무선 키보드', '{"Layout":"풀배열","Switch":"저소음 멤브레인","Connection":"2.4GHz, Bluetooth","Battery":"AAA 2개","Weight":"620g"}', 4.2, 154, 44),
(27, 'CodeType 87', 'NovaTech', 6, 99000, 129000, '/assets/keyboard.svg', '코딩에 적합한 텐키리스 기계식 키보드', '{"Layout":"87키","Switch":"갈축","Connection":"USB-C","Backlight":"화이트","Keycap":"PBT"}', 4.5, 121, 26),
(28, 'GameStrike RGB', 'Aster', 6, 139000, 169000, '/assets/keyboard.svg', '빠른 입력과 RGB를 갖춘 게이밍 키보드', '{"Layout":"풀배열","Switch":"적축","Connection":"USB-C","Polling":"1000Hz","Backlight":"RGB"}', 4.4, 97, 21),
(29, 'SilentKeys Mini', 'Mellow', 6, 69000, 89000, '/assets/keyboard.svg', '작은 책상에 맞는 저소음 미니 키보드', '{"Layout":"68키","Switch":"저소음 리니어","Connection":"Bluetooth","Battery":"2000mAh","Weight":"510g"}', 4.3, 86, 31),
(30, 'ErgoWave K', 'Eon', 6, 119000, 149000, '/assets/keyboard.svg', '손목 부담을 줄인 인체공학 키보드', '{"Layout":"분리형 곡선","Switch":"펜타그래프","Connection":"Bluetooth","PalmRest":"포함","Battery":"충전식"}', 4.1, 63, 19),

(31, 'ClickMate Silent', 'Hanbit', 7, 29000, 39000, '/assets/mouse.svg', '도서관과 사무실에서 쓰기 좋은 무소음 마우스', '{"DPI":"1600","Connection":"2.4GHz","Buttons":"5개","Battery":"AA 1개","Weight":"88g"}', 4.2, 201, 63),
(32, 'GameAim 8K', 'Aster', 7, 89000, 119000, '/assets/mouse.svg', '정밀 센서를 갖춘 게이밍 마우스', '{"DPI":"26000","Connection":"유선 USB-C","Buttons":"8개","Polling":"8000Hz","Weight":"59g"}', 4.6, 133, 24),
(33, 'TravelMini Mouse', 'Eon', 7, 24000, 34000, '/assets/mouse.svg', '노트북 가방에 넣기 좋은 휴대용 마우스', '{"DPI":"1200","Connection":"Bluetooth","Buttons":"3개","Battery":"AAA 1개","Weight":"62g"}', 4.0, 144, 58),
(34, 'ErgoGrip Pro', 'Mellow', 7, 69000, 89000, '/assets/mouse.svg', '장시간 작업에 맞춘 인체공학 마우스', '{"DPI":"4000","Connection":"Bluetooth, 2.4GHz","Buttons":"6개","Battery":"충전식","Angle":"57도"}', 4.4, 102, 22),
(35, 'DualConnect M', 'NovaTech', 7, 49000, 69000, '/assets/mouse.svg', '여러 기기를 오가며 쓰는 멀티페어링 마우스', '{"DPI":"3200","Connection":"Bluetooth, 2.4GHz","Buttons":"6개","Device":"3대 전환","Battery":"충전식"}', 4.3, 87, 35),

(36, 'FitWatch Daily', 'NovaTech', 8, 129000, 159000, '/assets/smartwatch.svg', '알림과 운동 기록 중심의 기본형 스마트워치', '{"Display":"1.6인치 AMOLED","Battery":"7일","GPS":"연결 GPS","Health":"심박, 수면","Waterproof":"5ATM"}', 4.2, 176, 39),
(37, 'HealthRing Watch', 'Mellow', 8, 199000, 239000, '/assets/smartwatch.svg', '부모님 건강 체크에 초점을 둔 스마트워치', '{"Display":"1.8인치","Battery":"6일","GPS":"내장 GPS","Health":"심박, 혈중산소","Button":"큰 글씨 모드"}', 4.4, 118, 26),
(38, 'RunMate GPS', 'Aster', 8, 249000, 299000, '/assets/smartwatch.svg', '러닝과 야외 운동에 맞춘 GPS 스마트워치', '{"Display":"1.4인치 AMOLED","Battery":"10일","GPS":"멀티밴드","Health":"심박, VO2max","Waterproof":"5ATM"}', 4.6, 92, 17),
(39, 'StyleWatch Mini', 'Eon', 8, 99000, 129000, '/assets/smartwatch.svg', '가볍게 착용하기 좋은 입문형 스마트워치', '{"Display":"1.3인치","Battery":"5일","GPS":"연결 GPS","Health":"심박, 수면","Weight":"32g"}', 4.0, 84, 33),
(40, 'WorkSync Watch', 'Hanbit', 8, 169000, 209000, '/assets/smartwatch.svg', '일정 알림과 통화 기능을 강화한 스마트워치', '{"Display":"1.7인치 AMOLED","Battery":"7일","GPS":"내장 GPS","Call":"블루투스 통화","Health":"심박, 스트레스"}', 4.3, 101, 28);

INSERT INTO reviews (product_id, user_name, rating, content, pros, cons, created_at)
SELECT
  p.id,
  r.user_name,
  LEAST(5.0, GREATEST(3.5, p.rating + r.delta))::numeric(2,1),
  format(r.content_template, p.name),
  format(r.pros_template, p.short_description),
  r.cons_text,
  NOW() - (r.days_ago || ' days')::interval
FROM products p
CROSS JOIN (
  VALUES
    ('민지', 0.1, '%s를 일주일 정도 써봤는데 기본기는 만족스럽습니다. 가격대와 성능의 균형이 괜찮습니다.', '가장 마음에 든 점은 %s라는 점입니다.', '고급 기능이나 구성품은 제품별로 확인이 필요합니다.', 3),
    ('준호', -0.2, '%s는 실사용에서 큰 불편은 없었지만 기대보다 아쉬운 부분도 있었습니다.', '설치나 사용 방법이 어렵지 않아 처음 쓰기 편했습니다.', '마감이나 소음, 무게 같은 체감 요소는 사람에 따라 다를 수 있습니다.', 9),
    ('서연', 0.0, '%s를 비슷한 가격대 제품과 비교하다가 선택했습니다. 전체적으로 무난한 선택입니다.', '가격 대비 필요한 기능을 잘 갖춘 편입니다.', '세부 스펙을 꼼꼼히 비교하고 사는 것이 좋습니다.', 15)
) AS r(user_name, delta, content_template, pros_template, cons_text, days_ago);

SELECT setval('categories_id_seq', (SELECT MAX(id) FROM categories));
SELECT setval('products_id_seq', (SELECT MAX(id) FROM products));
SELECT setval('reviews_id_seq', (SELECT MAX(id) FROM reviews));

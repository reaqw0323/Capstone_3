import os
import re
import secrets
from decimal import Decimal
from pathlib import Path
from datetime import datetime
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from psycopg.types.json import Jsonb

from .db import get_connection


app = FastAPI(title="EasyPick AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "easypick-ai")
PROMPT_DIR = Path(os.getenv("PROMPT_DIR", "/app/ai_prompts"))

CATEGORY_KEYWORDS = {
    "노트북": ["노트북", "랩탑", "코딩", "과제", "휴대용 작업"],
    "모니터": ["모니터", "디스플레이", "게임용 모니터", "화면"],
    "무선청소기": ["무선청소기", "청소기", "청소", "자취방"],
    "공기청정기": ["공기청정기", "공기", "미세먼지", "부모님"],
    "이어폰": ["이어폰", "무선 이어폰", "버즈", "통화", "음악"],
    "키보드": ["키보드", "기계식", "타건", "코딩 키보드"],
    "마우스": ["마우스", "무소음 마우스", "게이밍 마우스"],
    "스마트워치": ["스마트워치", "워치", "건강", "운동 기록"],
}


class RecommendRequest(BaseModel):
    message: str = Field(..., min_length=1)


class CompareRequest(BaseModel):
    product_ids: list[int] = Field(..., min_length=1)
    criteria: str | None = None


class ReviewSummaryRequest(BaseModel):
    product_id: int


class ProductWriteRequest(BaseModel):
    name: str = Field(..., min_length=1)
    brand: str = Field(..., min_length=1)
    category_id: int
    price: int = Field(..., ge=0)
    original_price: int | None = Field(default=None, ge=0)
    image_url: str = Field(default="/assets/laptop.svg", min_length=1)
    short_description: str = ""
    specs: dict[str, Any] = Field(default_factory=dict)
    rating: float = Field(default=0, ge=0, le=5)
    review_count: int = Field(default=0, ge=0)
    stock: int = Field(default=0, ge=0)


class CartItemRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    product_id: int
    quantity: int = Field(default=1, ge=1, le=99)


class CartQuantityRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    quantity: int = Field(..., ge=1, le=99)


class CheckoutRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    customer_name: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=1)
    address: str = Field(..., min_length=1)
    delivery_memo: str | None = None
    payment_method: str = Field(..., min_length=1)


class OrderStatusRequest(BaseModel):
    status: str = Field(..., min_length=1)


def normalize(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    return value


def product_from_row(row: dict[str, Any]) -> dict[str, Any]:
    product = normalize(dict(row))
    product["category"] = product.pop("category_name", None)
    return product


def read_prompt(name: str, fallback: str) -> str:
    path = PROMPT_DIR / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    return fallback


def final_answer_instructions() -> str:
    return (
        "중요 지시:\n"
        "- 사고 과정, 추론 과정, 내부 검토 내용을 출력하지 마세요.\n"
        "- 영어로 생각을 설명하지 마세요.\n"
        "- 영어 문장을 출력하지 마세요.\n"
        "- 최종 답변만 한국어로 작성하세요.\n"
        "- 상품명과 브랜드명을 제외한 모든 설명은 한국어로만 작성하세요.\n"
        "- 제공된 상품 후보에 없는 정보는 절대 쓰지 마세요.\n\n"
    )


def clean_ai_answer(answer: str) -> str:
    cleaned = answer.strip()
    markers = ["최종 답변:", "답변:", "추천 1순위"]
    for marker in markers:
        index = cleaned.find(marker)
        if index > 0:
            cleaned = cleaned[index:]
            break
    if cleaned.lower().startswith(("okay,", "let's", "we need", "the user")):
        korean_index = min(
            [idx for idx in [cleaned.find("1."), cleaned.find("추천"), cleaned.find("제공된")] if idx >= 0]
            or [-1]
        )
        if korean_index >= 0:
            cleaned = cleaned[korean_index:]
    return cleaned or "AI 응답을 생성하지 못했습니다."


def parse_price(message: str) -> tuple[int | None, int | None]:
    compact = message.replace(" ", "")

    range_match = re.search(r"(\d+)만원대", compact)
    if range_match:
        base = int(range_match.group(1)) * 10000
        return base, base + 99999

    max_match = re.search(r"(\d+)만원?(이하|안쪽|미만|까지|내|아래)", compact)
    if max_match:
        return None, int(max_match.group(1)) * 10000

    won_match = re.search(r"(\d{5,})원?(이하|안쪽|미만|까지|내|아래)", compact)
    if won_match:
        return None, int(won_match.group(1))

    return None, None


def detect_category(message: str) -> str | None:
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in message for keyword in keywords):
            return category
    return None


def search_products(
    query: str | None = None,
    category: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    brand: str | None = None,
    sort: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    where = []
    params: list[Any] = []

    if query:
        like = f"%{query}%"
        where.append(
            "(p.name ILIKE %s OR p.brand ILIKE %s OR c.name ILIKE %s "
            "OR p.short_description ILIKE %s OR p.specs::text ILIKE %s)"
        )
        params.extend([like, like, like, like, like])

    if category:
        if str(category).isdigit():
            where.append("p.category_id = %s")
            params.append(int(category))
        else:
            where.append("c.name = %s")
            params.append(category)

    if min_price is not None:
        where.append("p.price >= %s")
        params.append(min_price)

    if max_price is not None:
        where.append("p.price <= %s")
        params.append(max_price)

    if brand:
        where.append("p.brand ILIKE %s")
        params.append(f"%{brand}%")

    order_by = {
        "price_asc": "p.price ASC",
        "price_desc": "p.price DESC",
        "rating": "p.rating DESC, p.review_count DESC",
        "review": "p.review_count DESC",
        "new": "p.created_at DESC",
    }.get(sort or "", "p.rating DESC, p.review_count DESC")

    sql = """
        SELECT p.*, c.name AS category_name
        FROM products p
        JOIN categories c ON c.id = p.category_id
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY {order_by}"
    if limit:
        sql += " LIMIT %s"
        params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [product_from_row(row) for row in rows]


def get_product(product_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT p.*, c.name AS category_name
            FROM products p
            JOIN categories c ON c.id = p.category_id
            WHERE p.id = %s
            """,
            [product_id],
        ).fetchone()
    return product_from_row(row) if row else None


def get_products_by_ids(product_ids: list[int]) -> list[dict[str, Any]]:
    if not product_ids:
        return []
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT p.*, c.name AS category_name
            FROM products p
            JOIN categories c ON c.id = p.category_id
            WHERE p.id = ANY(%s::int[])
            ORDER BY array_position(%s::int[], p.id)
            """,
            [product_ids, product_ids],
        ).fetchall()
    return [product_from_row(row) for row in rows]


def get_reviews(product_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, product_id, user_name, rating, content, pros, cons, created_at
            FROM reviews
            WHERE product_id = %s
            ORDER BY created_at DESC
            """,
            [product_id],
        ).fetchall()
    return normalize([dict(row) for row in rows])


def cart_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    items = []
    total_price = 0
    total_quantity = 0
    for row in rows:
        product = {
            "id": row["product_id"],
            "name": row["name"],
            "brand": row["brand"],
            "category_id": row["category_id"],
            "category": row["category_name"],
            "price": row["price"],
            "original_price": row["original_price"],
            "image_url": row["image_url"],
            "short_description": row["short_description"],
            "specs": row["specs"],
            "rating": row["rating"],
            "review_count": row["review_count"],
            "stock": row["stock"],
        }
        quantity = row["quantity"]
        subtotal = row["subtotal"]
        total_price += subtotal
        total_quantity += quantity
        items.append(
            {
                "id": row["cart_item_id"],
                "quantity": quantity,
                "subtotal": subtotal,
                "product": normalize(product),
            }
        )
    return {"items": items, "total_price": total_price, "total_quantity": total_quantity}


def get_cart_data(session_id: str) -> dict[str, Any]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                ci.id AS cart_item_id,
                ci.quantity,
                (ci.quantity * p.price)::int AS subtotal,
                p.id AS product_id,
                p.*,
                c.name AS category_name
            FROM cart_items ci
            JOIN products p ON p.id = ci.product_id
            JOIN categories c ON c.id = p.category_id
            WHERE ci.session_id = %s
            ORDER BY ci.created_at DESC
            """,
            [session_id],
        ).fetchall()
    return cart_from_rows(rows)


def order_from_id(order_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        order = conn.execute(
            """
            SELECT id, order_number, session_id, customer_name, phone, address,
                   delivery_memo, payment_method, total_price, status, created_at
            FROM orders
            WHERE id = %s
            """,
            [order_id],
        ).fetchone()
        if not order:
            return None
        items = conn.execute(
            """
            SELECT id, product_id, product_name, brand, image_url, price, quantity, subtotal
            FROM order_items
            WHERE order_id = %s
            ORDER BY id
            """,
            [order_id],
        ).fetchall()
    result = normalize(dict(order))
    result["items"] = normalize([dict(item) for item in items])
    return result


def order_from_number(order_number: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM orders WHERE order_number = %s",
            [order_number],
        ).fetchone()
    return order_from_id(row["id"]) if row else None


def create_order_number() -> str:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"SS{stamp}{secrets.token_hex(2).upper()}"


def review_summary_text(product_id: int) -> str:
    reviews = get_reviews(product_id)
    if not reviews:
        return "등록된 리뷰가 없습니다."
    snippets = []
    for review in reviews[:5]:
        snippets.append(
            f"- 평점 {review['rating']}: 장점 {review.get('pros') or '정보 없음'} / "
            f"아쉬운 점 {review.get('cons') or '정보 없음'}"
        )
    return "\n".join(snippets)


def format_products_for_prompt(products: list[dict[str, Any]]) -> str:
    lines = []
    for index, product in enumerate(products, start=1):
        specs = ", ".join(f"{key}: {value}" for key, value in product["specs"].items())
        lines.append(
            f"{index}. 상품명: {product['name']}\n"
            f"   브랜드: {product['brand']}\n"
            f"   가격: {product['price']}원\n"
            f"   카테고리: {product['category']}\n"
            f"   주요 스펙: {specs}\n"
            f"   평점: {product['rating']}점, 리뷰 수: {product['review_count']}개\n"
            f"   리뷰 요약: {review_summary_text(product['id'])}"
        )
    return "\n\n".join(lines)


async def call_ollama(prompt: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "너는 EasyPick의 한국어 쇼핑 도우미다. "
                    "사고 과정은 숨기고 최종 답변만 한국어로 작성한다. "
                    "상품명과 브랜드명을 제외하고 영어 문장을 쓰지 않는다."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 180,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError:
        return (
            "AI 서버에 연결하지 못했습니다. Ollama 컨테이너와 easypick-ai 모델이 "
            "준비되었는지 확인해 주세요."
        )
    message = data.get("message") or {}
    answer = message.get("content") or data.get("response") or ""
    return clean_ai_answer(answer)


def needs_korean_fallback(answer: str) -> bool:
    if not answer.strip():
        return True
    lowered = answer.lower().strip()
    english_markers = ["okay,", "let's", "the user", "we need", "first,", "so,"]
    if lowered.startswith(tuple(english_markers)):
        return True
    korean_chars = len(re.findall(r"[가-힣]", answer))
    latin_chars = len(re.findall(r"[A-Za-z]", answer))
    return korean_chars < 20 and latin_chars > korean_chars


def fallback_recommendation(products: list[dict[str, Any]], user_message: str) -> str:
    top_products = products[:3]
    lines = [
        "1. 추천 1순위",
        f"   - 상품명: {top_products[0]['name']}",
        (
            f"   - 추천 이유: {top_products[0]['price']:,}원 가격대와 "
            f"평점 {top_products[0]['rating']}점을 기준으로 조건에 가장 잘 맞습니다."
        ),
        f"   - 장점: {top_products[0]['short_description']}",
        "   - 아쉬운 점: 제공된 리뷰와 스펙만으로는 장기 내구성은 확인하기 어렵습니다.",
        "   - 구매 전 확인할 점: 실제 사용 공간, 보관 위치, 필요한 흡입력과 사용 시간을 확인하세요.",
        "",
        "2. 비교 요약",
    ]
    for product in top_products:
        specs = ", ".join(f"{key}: {value}" for key, value in product["specs"].items())
        lines.append(
            f"   - {product['name']}: {product['price']:,}원, 평점 {product['rating']}점, {specs}"
        )
    lines.extend(
        [
            "",
            "3. 최종 한 줄 추천",
            f"   - '{user_message}' 조건에서는 {top_products[0]['name']}를 먼저 확인하는 것이 좋습니다.",
        ]
    )
    return "\n".join(lines)


def fallback_compare(products: list[dict[str, Any]], criteria: str | None) -> str:
    lines = [
        "상품 비교 요약",
        f"- 비교 기준: {criteria or '가격, 스펙, 평점, 리뷰'}",
        "",
    ]
    cheapest = min(products, key=lambda item: item["price"])
    highest_rating = max(products, key=lambda item: item["rating"])
    for product in products:
        specs = ", ".join(f"{key}: {value}" for key, value in product["specs"].items())
        lines.append(
            f"- {product['name']}: {product['price']:,}원, 브랜드 {product['brand']}, "
            f"평점 {product['rating']}점, 리뷰 {product['review_count']}개, 주요 스펙 {specs}"
        )
    lines.extend(
        [
            "",
            f"가격만 보면 {cheapest['name']}가 가장 부담이 적습니다.",
            f"평점 기준으로는 {highest_rating['name']}가 가장 높습니다.",
            "제공된 정보 외 배송, 할인, 추가 구성품은 확인하기 어렵습니다.",
        ]
    )
    return "\n".join(lines)


def fallback_review_summary(product: dict[str, Any], reviews: list[dict[str, Any]]) -> str:
    pros = [review.get("pros") for review in reviews if review.get("pros")]
    cons = [review.get("cons") for review in reviews if review.get("cons")]
    return "\n".join(
        [
            "1. 반복적으로 언급된 장점",
            *(f"   - {item}" for item in pros[:3]),
            "",
            "2. 반복적으로 언급된 아쉬운 점",
            *(f"   - {item}" for item in cons[:3]),
            "",
            "3. 구매 전 확인할 점",
            "   - 리뷰에 없는 고장 사례, 배송 품질, 장기 내구성은 제공된 정보만으로는 확인하기 어렵습니다.",
            "",
            "4. 한 줄 요약",
            f"   - {product['name']}는 제공된 리뷰 기준으로 장단점이 비교적 명확한 상품입니다.",
        ]
    )


def save_ai_log(message: str, answer: str, product_ids: list[int]) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO ai_logs (user_message, ai_response, product_ids)
            VALUES (%s, %s, %s)
            """,
            [message, answer, product_ids],
        )


@app.get("/api/health")
def health_check():
    return {"status": "ok", "ollama_model": OLLAMA_MODEL}


@app.get("/api/categories")
def list_categories():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, description FROM categories ORDER BY id"
        ).fetchall()
    return normalize([dict(row) for row in rows])


@app.get("/api/products")
def list_products(
    query: str | None = None,
    category: str | None = None,
    minPrice: int | None = Query(default=None, ge=0),
    maxPrice: int | None = Query(default=None, ge=0),
    brand: str | None = None,
    sort: str | None = None,
):
    return search_products(
        query=query,
        category=category,
        min_price=minPrice,
        max_price=maxPrice,
        brand=brand,
        sort=sort,
    )


@app.get("/api/products/compare")
def compare_products(ids: str):
    try:
        product_ids = [int(item) for item in ids.split(",") if item.strip()]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="ids는 숫자 목록이어야 합니다.") from exc
    return get_products_by_ids(product_ids)


@app.get("/api/products/{product_id}")
def product_detail(product_id: int):
    product = get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")
    return product


@app.get("/api/products/{product_id}/reviews")
def product_reviews(product_id: int):
    if not get_product(product_id):
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")
    return get_reviews(product_id)


@app.post("/api/admin/products")
def create_product(request: ProductWriteRequest):
    with get_connection() as conn:
        category = conn.execute(
            "SELECT id FROM categories WHERE id = %s",
            [request.category_id],
        ).fetchone()
        if not category:
            raise HTTPException(status_code=400, detail="Category not found.")

        row = conn.execute(
            """
            INSERT INTO products (
                name, brand, category_id, price, original_price, image_url,
                short_description, specs, rating, review_count, stock
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            [
                request.name,
                request.brand,
                request.category_id,
                request.price,
                request.original_price,
                request.image_url,
                request.short_description,
                Jsonb(request.specs),
                request.rating,
                request.review_count,
                request.stock,
            ],
        ).fetchone()
    return get_product(row["id"])


@app.put("/api/admin/products/{product_id}")
def update_product(product_id: int, request: ProductWriteRequest):
    with get_connection() as conn:
        category = conn.execute(
            "SELECT id FROM categories WHERE id = %s",
            [request.category_id],
        ).fetchone()
        if not category:
            raise HTTPException(status_code=400, detail="Category not found.")

        row = conn.execute(
            """
            UPDATE products
            SET name = %s,
                brand = %s,
                category_id = %s,
                price = %s,
                original_price = %s,
                image_url = %s,
                short_description = %s,
                specs = %s,
                rating = %s,
                review_count = %s,
                stock = %s,
                updated_at = NOW()
            WHERE id = %s
            RETURNING id
            """,
            [
                request.name,
                request.brand,
                request.category_id,
                request.price,
                request.original_price,
                request.image_url,
                request.short_description,
                Jsonb(request.specs),
                request.rating,
                request.review_count,
                request.stock,
                product_id,
            ],
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Product not found.")
    return get_product(product_id)


@app.delete("/api/admin/products/{product_id}")
def delete_product(product_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "DELETE FROM products WHERE id = %s RETURNING id",
            [product_id],
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Product not found.")
    return {"ok": True, "deleted_id": product_id}


@app.get("/api/cart")
def get_cart(sessionId: str):
    return get_cart_data(sessionId)


@app.post("/api/cart/items")
def add_cart_item(request: CartItemRequest):
    product = get_product(request.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    if product["stock"] <= 0:
        raise HTTPException(status_code=400, detail="Out of stock.")

    quantity = min(request.quantity, product["stock"])
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO cart_items (session_id, product_id, quantity)
            VALUES (%s, %s, %s)
            ON CONFLICT (session_id, product_id)
            DO UPDATE SET quantity = LEAST(cart_items.quantity + EXCLUDED.quantity, %s)
            """,
            [request.session_id, request.product_id, quantity, product["stock"]],
        )
    return get_cart_data(request.session_id)


@app.put("/api/cart/items/{cart_item_id}")
def update_cart_item(cart_item_id: int, request: CartQuantityRequest):
    with get_connection() as conn:
        row = conn.execute(
            """
            UPDATE cart_items ci
            SET quantity = LEAST(%s, p.stock)
            FROM products p
            WHERE ci.product_id = p.id
              AND ci.id = %s
              AND ci.session_id = %s
            RETURNING ci.id
            """,
            [request.quantity, cart_item_id, request.session_id],
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Cart item not found.")
    return get_cart_data(request.session_id)


@app.delete("/api/cart/items/{cart_item_id}")
def delete_cart_item(cart_item_id: int, sessionId: str):
    with get_connection() as conn:
        row = conn.execute(
            "DELETE FROM cart_items WHERE id = %s AND session_id = %s RETURNING id",
            [cart_item_id, sessionId],
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Cart item not found.")
    return get_cart_data(sessionId)


@app.delete("/api/cart")
def clear_cart(sessionId: str):
    with get_connection() as conn:
        conn.execute("DELETE FROM cart_items WHERE session_id = %s", [sessionId])
    return {"items": [], "total_price": 0, "total_quantity": 0}


@app.post("/api/orders")
def create_order(request: CheckoutRequest):
    with get_connection() as conn:
        cart_rows = conn.execute(
            """
            SELECT
                ci.id AS cart_item_id,
                ci.quantity,
                p.id AS product_id,
                p.name,
                p.brand,
                p.image_url,
                p.price,
                p.stock,
                (ci.quantity * p.price)::int AS subtotal
            FROM cart_items ci
            JOIN products p ON p.id = ci.product_id
            WHERE ci.session_id = %s
            ORDER BY ci.created_at
            """,
            [request.session_id],
        ).fetchall()

        if not cart_rows:
            raise HTTPException(status_code=400, detail="Cart is empty.")

        for row in cart_rows:
            if row["stock"] < row["quantity"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"{row['name']} stock is not enough.",
                )

        total_price = sum(row["subtotal"] for row in cart_rows)
        order_number = create_order_number()
        order = conn.execute(
            """
            INSERT INTO orders (
                order_number, session_id, customer_name, phone, address,
                delivery_memo, payment_method, total_price
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            [
                order_number,
                request.session_id,
                request.customer_name,
                request.phone,
                request.address,
                request.delivery_memo,
                request.payment_method,
                total_price,
            ],
        ).fetchone()

        for row in cart_rows:
            conn.execute(
                """
                INSERT INTO order_items (
                    order_id, product_id, product_name, brand, image_url,
                    price, quantity, subtotal
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    order["id"],
                    row["product_id"],
                    row["name"],
                    row["brand"],
                    row["image_url"],
                    row["price"],
                    row["quantity"],
                    row["subtotal"],
                ],
            )
            conn.execute(
                "UPDATE products SET stock = GREATEST(stock - %s, 0) WHERE id = %s",
                [row["quantity"], row["product_id"]],
            )

        conn.execute("DELETE FROM cart_items WHERE session_id = %s", [request.session_id])

    return order_from_id(order["id"])


@app.get("/api/orders")
def list_orders(sessionId: str):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, order_number, customer_name, payment_method, total_price,
                   status, created_at
            FROM orders
            WHERE session_id = %s
            ORDER BY created_at DESC
            """,
            [sessionId],
        ).fetchall()
    return normalize([dict(row) for row in rows])


@app.get("/api/orders/{order_number}")
def get_order(order_number: str):
    order = order_from_number(order_number)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    return order


@app.get("/api/admin/orders")
def admin_list_orders():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, order_number, customer_name, phone, payment_method,
                   total_price, status, created_at
            FROM orders
            ORDER BY created_at DESC
            """,
        ).fetchall()
    return normalize([dict(row) for row in rows])


@app.patch("/api/admin/orders/{order_id}/status")
def admin_update_order_status(order_id: int, request: OrderStatusRequest):
    allowed = {"주문 접수", "결제 확인", "배송 준비", "배송 중", "배송 완료", "주문 취소"}
    if request.status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid order status.")

    with get_connection() as conn:
        row = conn.execute(
            """
            UPDATE orders
            SET status = %s
            WHERE id = %s
            RETURNING id
            """,
            [request.status, order_id],
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Order not found.")
    return order_from_id(order_id)


@app.post("/api/ai/recommend")
async def ai_recommend(request: RecommendRequest):
    category = detect_category(request.message)
    min_price, max_price = parse_price(request.message)
    candidates = search_products(
        query=None if category else request.message,
        category=category,
        min_price=min_price,
        max_price=max_price,
        sort="rating",
        limit=10,
    )

    if not candidates:
        return {
            "answer": "조건에 맞는 상품을 찾지 못했습니다. 예산이나 카테고리를 조금 넓혀서 다시 검색해 주세요.",
            "products": [],
            "filters": {"category": category, "minPrice": min_price, "maxPrice": max_price},
        }

    template = read_prompt(
        "recommend_prompt.txt",
        "사용자 질문:\n{message}\n\n상품 후보:\n{products}\n\n반드시 한국어로 답변하세요.",
    )
    prompt = final_answer_instructions() + template.format(
        message=request.message,
        products=format_products_for_prompt(candidates),
    )
    answer = await call_ollama(prompt)
    if needs_korean_fallback(answer):
        answer = fallback_recommendation(candidates, request.message)
    product_ids = [product["id"] for product in candidates]
    save_ai_log(request.message, answer, product_ids)
    return {
        "answer": answer,
        "products": candidates,
        "filters": {"category": category, "minPrice": min_price, "maxPrice": max_price},
    }


@app.post("/api/ai/compare")
async def ai_compare(request: CompareRequest):
    products = get_products_by_ids(request.product_ids)
    if len(products) < 2:
        return {"answer": "상품이 2개 이상 선택되어야 비교할 수 있습니다.", "products": products}

    template = read_prompt(
        "compare_prompt.txt",
        "사용자 비교 기준:\n{criteria}\n\n비교 상품:\n{products}\n\n한국어로 답변하세요.",
    )
    prompt = final_answer_instructions() + template.format(
        criteria=request.criteria or "가격, 스펙, 평점, 리뷰 기준으로 비교",
        products=format_products_for_prompt(products),
    )
    answer = await call_ollama(prompt)
    if needs_korean_fallback(answer):
        answer = fallback_compare(products, request.criteria)
    save_ai_log(request.criteria or "상품 비교", answer, [product["id"] for product in products])
    return {"answer": answer, "products": products}


@app.post("/api/ai/review-summary")
async def ai_review_summary(request: ReviewSummaryRequest):
    product = get_product(request.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")
    reviews = get_reviews(request.product_id)
    if not reviews:
        return {"answer": "아직 등록된 리뷰가 없습니다.", "product": product}

    review_lines = "\n".join(
        f"- {review['user_name']} / 평점 {review['rating']}: {review['content']} "
        f"(장점: {review.get('pros') or '정보 없음'}, 단점: {review.get('cons') or '정보 없음'})"
        for review in reviews
    )
    template = read_prompt(
        "review_summary_prompt.txt",
        "상품명:\n{product_name}\n\n리뷰:\n{reviews}\n\n한국어로 요약하세요.",
    )
    prompt = final_answer_instructions() + template.format(product_name=product["name"], reviews=review_lines)
    answer = await call_ollama(prompt)
    if needs_korean_fallback(answer):
        answer = fallback_review_summary(product, reviews)
    save_ai_log(f"리뷰 요약: {product['name']}", answer, [product["id"]])
    return {"answer": answer, "product": product}

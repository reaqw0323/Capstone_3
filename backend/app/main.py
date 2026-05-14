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

AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama").strip().lower()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "easypick-ai")
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
LMSTUDIO_BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1").rstrip("/")
LMSTUDIO_MODEL = os.getenv("LMSTUDIO_MODEL", "local-model")
LMSTUDIO_API_KEY = os.getenv("LMSTUDIO_API_KEY", "")
LMSTUDIO_TIMEOUT_SECONDS = float(os.getenv("LMSTUDIO_TIMEOUT_SECONDS", "240"))
LMSTUDIO_CONTEXT_LENGTH = int(os.getenv("LMSTUDIO_CONTEXT_LENGTH", "8192"))
AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "900"))
PROMPT_CONTEXT_BUFFER_TOKENS = int(os.getenv("PROMPT_CONTEXT_BUFFER_TOKENS", "1200"))
PROMPT_CHAR_BUDGET = int(os.getenv("PROMPT_CHAR_BUDGET", "0"))
PROMPT_DIR = Path(os.getenv("PROMPT_DIR", "/app/ai_prompts"))

AI_SYSTEM_PROMPT = (
    "너는 EasyPick의 한국어 쇼핑 도우미다. "
    "친근하고 자연스럽게 말하되, 상품 정보는 정확하게 다룬다. "
    "사고 과정은 숨기고 최종 답변만 한국어로 작성한다. "
    "상품 후보에 없는 정보는 만들지 않는다. "
    "사용자가 짧게 말해도 의도를 잘 파악하고, 필요한 기준을 쉽게 잡아준다. "
    "추천, 비교, 리뷰 요약 모두 사용자가 실제로 고르기 쉬워지도록 설명한다."
)

LMSTUDIO_PROVIDER_NAMES = {"lmstudio", "lm-studio", "lm_studio"}


def normalize_ai_provider(provider: str | None) -> str:
    value = (provider or "ollama").strip().lower()
    if value in LMSTUDIO_PROVIDER_NAMES:
        return "lmstudio"
    return "ollama" if value == "ollama" else value


def trim_url(url: str) -> str:
    return url.strip().rstrip("/")


def lmstudio_root_url(base_url: str) -> str:
    url = trim_url(base_url)
    return url[:-3] if url.endswith("/v1") else url


def lmstudio_openai_url(base_url: str) -> str:
    url = trim_url(base_url)
    return url if url.endswith("/v1") else f"{url}/v1"


def normalize_lmstudio_base_url(base_url: str) -> str:
    return lmstudio_openai_url(base_url)

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
    session_id: str | None = None
    sessionId: str | None = None


class CompareRequest(BaseModel):
    product_ids: list[int] = Field(..., min_length=1)
    criteria: str | None = None


class ReviewSummaryRequest(BaseModel):
    product_id: int


class AiSettingsRequest(BaseModel):
    provider: str = Field(default="ollama", min_length=1)
    ollama_base_url: str = Field(default="http://ollama:11434", min_length=1)
    ollama_model: str = Field(default="easypick-ai", min_length=1)
    lmstudio_base_url: str = Field(default="http://host.docker.internal:1234/v1", min_length=1)
    lmstudio_model: str = Field(default="local-model", min_length=1)
    lmstudio_api_key: str | None = None


class AiUnloadRequest(BaseModel):
    provider: str = Field(..., min_length=1)
    model: str | None = None


class ProductWriteRequest(BaseModel):
    name: str = Field(..., min_length=1)
    brand: str = Field(..., min_length=1)
    category_id: int
    price: int = Field(..., ge=0)
    original_price: int | None = Field(default=None, ge=0)
    image_url: str = Field(default="/assets/laptop.svg", min_length=1)
    short_description: str = ""
    detail_description: str = ""
    recommended_for: str = ""
    cautions: str = ""
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


def ensure_product_extra_columns() -> None:
    with get_connection() as conn:
        conn.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS detail_description TEXT NOT NULL DEFAULT ''")
        conn.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS recommended_for TEXT NOT NULL DEFAULT ''")
        conn.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS cautions TEXT NOT NULL DEFAULT ''")


def read_prompt(name: str, fallback: str) -> str:
    path = PROMPT_DIR / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    return fallback


def final_answer_instructions() -> str:
    return (
        "공통 답변 지시:\n"
        "- 내부 추론 과정은 출력하지 말고 최종 답변만 한국어로 작성하세요.\n"
        "- EasyPick DB에서 제공된 상품, 가격, 스펙, 리뷰, 상세설명, 추천대상, 주의사항만 근거로 사용하세요.\n"
        "- 없는 배송, 할인, AS, 장기 내구성, 외부 쇼핑몰 정보는 만들지 마세요.\n"
        "- 정보가 부족하면 딱딱하게 거절하지 말고 '제공된 정보만으로는 확인하기 어렵습니다'라고 자연스럽게 말하세요.\n"
        "- 말투는 친근한 쇼핑 상담원처럼 부드럽게 하세요. 사용자가 짧게 말해도 의도를 잘 받아주고, 필요한 경우 기준을 쉽게 잡아주세요.\n"
        "- 답변은 템플릿처럼 반복하지 말고 질문의 분위기에 맞게 짧게 또는 자세히 조절하세요.\n"
        "- 장점만 밀어붙이지 말고, 확인할 점도 솔직하게 알려주세요.\n"
        "- 마지막에는 사용자가 다음 선택을 할 수 있게 결론을 분명하게 정리하세요.\n\n"
    )


def clean_ai_answer(answer: str) -> str:
    cleaned = answer.strip()
    markers = ["최종 답변:", "답변:", "추천 1순위"]
    for marker in markers:
        index = cleaned.find(marker)
        if index > 0:
            cleaned = cleaned[index:]
            break
    internal_markers = [
        "사용자 의도 파악",
        "제약 조건 확인",
        "후보 상품 분석",
        "전략 수립",
        "추천 순서 및 근거",
        "답변 구성",
        "Thinking Process",
    ]
    if any(marker in cleaned[:800] for marker in internal_markers):
        starts = [
            cleaned.find("혹시"),
            cleaned.find("좋아요"),
            cleaned.find("네,"),
            cleaned.find("일단"),
            cleaned.find("현재"),
            cleaned.find("###"),
        ]
        visible_start = min([index for index in starts if index >= 0] or [-1])
        if visible_start > 0:
            cleaned = cleaned[visible_start:].strip()
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


def parse_requested_count(message: str) -> int | None:
    compact = message.replace(" ", "")
    korean_numbers = {
        "한": 1,
        "하나": 1,
        "두": 2,
        "둘": 2,
        "세": 3,
        "셋": 3,
        "네": 4,
        "넷": 4,
        "다섯": 5,
    }
    digit_match = re.search(r"(\d+)(개|가지|개만|가지만|개추천|개만추천)", compact)
    if digit_match:
        return max(1, min(int(digit_match.group(1)), 5))

    for word, count in korean_numbers.items():
        if re.search(fr"{word}(개|가지|개만|가지만|개추천|개만추천|개만골라|개골라|개만뽑아|개뽑아)", compact):
            return count

    if any(word in compact for word in ["하나만", "1순위만", "딱하나", "한개만"]):
        return 1
    return None


def extract_usage_context(message: str) -> str | None:
    usage_keywords = [
        "자취방",
        "원룸",
        "부모님",
        "게임용",
        "사무용",
        "휴대용",
        "대학생",
        "과제",
        "코딩",
        "영상편집",
        "청소",
        "운동",
        "통화",
        "음악",
        "조용한",
        "가성비",
    ]
    found = [keyword for keyword in usage_keywords if keyword in message]
    return ", ".join(found) if found else None


def is_shopping_intent(message: str, category: str | None, min_price: int | None, max_price: int | None) -> bool:
    normalized = message.strip()
    if len(normalized) < 3:
        return False
    if category or min_price is not None or max_price is not None:
        return True
    if is_cart_order_intent(normalized):
        return True
    shopping_terms = [
        "추천",
        "비교",
        "상품",
        "제품",
        "가격",
        "가성비",
        "살",
        "사고",
        "구매",
        "쓸만",
        "괜찮",
        "좋은",
        "리뷰",
        "스펙",
    ]
    return any(term in normalized for term in shopping_terms)


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
    ensure_product_extra_columns()
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
    ensure_product_extra_columns()
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
    ensure_product_extra_columns()
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


def compact_text(message: str) -> str:
    return re.sub(r"\s+", "", message.strip().lower())


def has_any_pattern(message: str, patterns: list[str]) -> bool:
    compact = compact_text(message)
    return any(re.search(pattern, compact) for pattern in patterns)


def wants_cart_info(message: str) -> bool:
    patterns = [
        r"장바구니",
        r"카트",
        r"담(은|아둔|아놓은|아논|긴|겨있는|겨둔|아둔것|아둔거)",
        r"넣(은|어둔|어놓은|어논|어둔것|어둔거)",
        r"보관(한|중인)",
        r"찜(한|해둔|해놓은|목록)",
    ]
    return has_any_pattern(message, patterns)


def wants_order_info(message: str) -> bool:
    patterns = [
        r"주문",
        r"주문내역",
        r"구매",
        r"구입",
        r"결제",
        r"배송",
        r"산(물건|상품|제품|거|것|내역|목록|리스트|아이템|물품|것들|거들)",
        r"샀(던|던거|던것|던물건|던상품|던제품|어|다|는지|던내역)",
        r"사(둔|놓은|논|봤던|본|버린)",
        r"전에(산|샀던|구매한|구입한|주문한)",
        r"내가(산|샀던|구매한|구입한|주문한)",
        r"구매(한|했던|내역|목록|상품|제품|물건|물품)",
        r"구입(한|했던|내역|목록|상품|제품|물건|물품)",
    ]
    return has_any_pattern(message, patterns)


def is_cart_order_intent(message: str) -> bool:
    return wants_cart_info(message) or wants_order_info(message)


def has_decision_intent(message: str) -> bool:
    patterns = [
        r"추천",
        r"비교",
        r"골라",
        r"고르",
        r"선택",
        r"뭐가(나아|좋아|괜찮)",
        r"어떤(게|거|것)",
        r"어느(게|거|것)",
        r"살까",
        r"사도",
        r"가성비",
        r"성능",
        r"장점",
        r"단점",
        r"차이",
        r"낫",
    ]
    return has_any_pattern(message, patterns)


def get_orders_for_session(session_id: str, limit: int = 5) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id
            FROM orders
            WHERE session_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            [session_id, limit],
        ).fetchall()
    orders = []
    for row in rows:
        order = order_from_id(row["id"])
        if order:
            orders.append(order)
    return orders


def cart_products_for_response(cart: dict[str, Any]) -> list[dict[str, Any]]:
    return [item["product"] for item in cart.get("items", [])]


def order_products_for_response(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    seen: set[int] = set()
    for order in orders:
        for item in order.get("items", []):
            product_id = item.get("product_id")
            if not product_id or product_id in seen:
                continue
            seen.add(product_id)
            products.append(
                {
                    "id": product_id,
                    "name": item.get("product_name"),
                    "brand": item.get("brand"),
                    "image_url": item.get("image_url"),
                    "price": item.get("price"),
                }
            )
    return products


def format_cart_context(cart: dict[str, Any]) -> str:
    items = cart.get("items", [])
    if not items:
        return "현재 장바구니는 비어 있습니다."
    lines = [
        f"현재 장바구니: 총 {cart.get('total_quantity', 0)}개, 합계 {cart.get('total_price', 0):,}원"
    ]
    for item in items:
        product = item["product"]
        lines.append(
            "- "
            f"{product['name']} / 브랜드 {product['brand']} / 카테고리 {product.get('category') or '정보 없음'} / "
            f"가격 {product['price']:,}원 / 수량 {item['quantity']}개 / 소계 {item['subtotal']:,}원"
        )
    return "\n".join(lines)


def format_order_context(orders: list[dict[str, Any]]) -> str:
    if not orders:
        return "현재 세션의 주문내역은 없습니다."
    lines = [f"최근 주문내역: {len(orders)}건"]
    for order in orders:
        item_text = ", ".join(
            f"{item.get('product_name')} {item.get('quantity')}개"
            for item in order.get("items", [])[:4]
        )
        if len(order.get("items", [])) > 4:
            item_text += " 외"
        lines.append(
            "- "
            f"주문번호 {order.get('order_number')} / 상태 {order.get('status')} / "
            f"결제금액 {order.get('total_price', 0):,}원 / 상품 {item_text or '정보 없음'}"
        )
    return "\n".join(lines)


def build_user_context(cart: dict[str, Any] | None, orders: list[dict[str, Any]] | None) -> str:
    sections = []
    if cart is not None and cart.get("items"):
        sections.append(format_cart_context(cart))
    if orders:
        sections.append(format_order_context(orders))
    if not sections:
        return "현재 요청에 사용할 장바구니나 주문내역 맥락은 없습니다."
    return "\n\n".join(sections)


def build_cart_order_direct_response(
    message: str,
    session_id: str | None,
) -> dict[str, Any] | None:
    if not is_cart_order_intent(message) or has_decision_intent(message):
        return None
    if not session_id:
        return {
            "answer": "현재 브라우저 세션 정보가 전달되지 않아 장바구니와 주문내역을 확인하기 어렵습니다. 사이트에서 AI 도우미를 다시 열어 질문해 주세요.",
            "products": [],
        }

    cart = get_cart_data(session_id)
    orders = get_orders_for_session(session_id)
    answer_parts = []
    products: list[dict[str, Any]] = []

    if wants_cart_info(message):
        answer_parts.append(format_cart_context(cart))
        products.extend(cart_products_for_response(cart))
    if wants_order_info(message):
        answer_parts.append(format_order_context(orders))
        products.extend(order_products_for_response(orders))

    if not answer_parts:
        return None
    return {
        "answer": "\n\n".join(answer_parts),
        "products": products,
    }


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


SPEC_LABELS = {
    "CPU": "CPU",
    "GPU": "GPU",
    "RAM": "메모리",
    "Storage": "저장장치",
    "Display": "화면",
    "Weight": "무게",
    "RefreshRate": "주사율",
    "Size": "화면 크기",
    "Panel": "패널",
    "Ports": "포트",
    "Resolution": "해상도",
    "Response": "응답속도",
    "Ratio": "화면 비율",
    "Color": "색 표현",
    "Suction": "흡입력",
    "Runtime": "사용 시간",
    "Filter": "필터",
    "Dustbin": "먼지통",
    "Coverage": "적용 면적",
    "Sensor": "센서",
    "Noise": "소음",
    "Mode": "모드",
    "Battery": "배터리",
    "Waterproof": "방수",
    "DPI": "DPI",
    "Buttons": "버튼 수",
    "Connection": "연결 방식",
    "OS": "운영체제",
    "Switch": "스위치",
    "Layout": "배열",
    "Driver": "드라이버",
    "ANC": "노이즈 캔슬링",
    "Codec": "코덱",
    "ChargingCase": "충전 케이스",
    "Health": "건강 측정",
    "SportsMode": "운동 모드",
    "Compatibility": "호환성",
}


SPEC_VALUE_LABELS = {
    "HEPA": "HEPA 필터",
    "IPS": "IPS 패널",
    "VA": "VA 패널",
    "HDMI, DP": "HDMI, DP",
}


def humanize_spec(key: str, value: Any) -> str:
    label = SPEC_LABELS.get(key, key)
    display_value = SPEC_VALUE_LABELS.get(str(value), str(value))
    return f"{label}: {display_value}"


def format_specs(specs: dict[str, Any], keys: list[str] | None = None) -> str:
    if keys:
        items = [(key, specs[key]) for key in keys if specs.get(key)]
    else:
        items = list(specs.items())
    return ", ".join(humanize_spec(key, value) for key, value in items)


def compact_prompt_text(value: Any, max_chars: int = 260) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rstrip()
    sentence_end = max(cut.rfind("."), cut.rfind("!"), cut.rfind("?"), cut.rfind("다."))
    if sentence_end >= max_chars * 0.55:
        cut = cut[: sentence_end + 1].rstrip()
    return f"{cut}..."


def prompt_char_budget(settings: dict[str, Any] | None = None) -> int:
    if PROMPT_CHAR_BUDGET > 0:
        return PROMPT_CHAR_BUDGET

    try:
        active_settings = settings or get_ai_settings()
        provider = normalize_ai_provider(active_settings.get("provider"))
    except Exception:
        provider = normalize_ai_provider(AI_PROVIDER)

    context_tokens = LMSTUDIO_CONTEXT_LENGTH if provider == "lmstudio" else OLLAMA_NUM_CTX
    usable_tokens = max(1200, context_tokens - PROMPT_CONTEXT_BUFFER_TOKENS)
    return max(2200, int(usable_tokens * 0.9))


def render_prompt(template: str, fields: dict[str, Any]) -> str:
    return final_answer_instructions() + template.format(**fields)


def product_prompt_card(product: dict[str, Any], index: int, detail_level: str = "full") -> str:
    name = product.get("name") or "상품명 없음"
    brand = product.get("brand") or "브랜드 정보 없음"
    category = product.get("category") or "카테고리 정보 없음"
    price = f"{int(product.get('price') or 0):,}원"
    short_description = compact_prompt_text(product.get("short_description"), 180)
    detail_description = compact_prompt_text(product.get("detail_description"), 260)
    recommended_for = compact_prompt_text(product.get("recommended_for"), 220)
    cautions = compact_prompt_text(product.get("cautions"), 220)
    specs = compact_prompt_text(format_specs(product.get("specs") or {}), 260)
    review_summary = compact_prompt_text(review_summary_text(product["id"]), 360)
    rating = product.get("rating")
    review_count = product.get("review_count")

    first_line = (
        f"{index}. {name}은 {brand}의 {category} 상품입니다. "
        f"가격은 {price}이고, 한마디로 보면 {short_description or '기본 정보가 많지는 않은 후보'}입니다."
    )

    if detail_level == "compact":
        return (
            f"{first_line} 주요 스펙은 {specs or '제공된 정보가 적습니다'}. "
            f"평점은 {rating}점, 리뷰는 {review_count}개입니다."
        )

    lines = [
        first_line,
        f"   주요 스펙은 {specs or '제공된 정보가 적습니다'}.",
        f"   사용자 반응은 평점 {rating}점, 리뷰 {review_count}개 기준으로 볼 수 있습니다.",
    ]

    if recommended_for:
        lines.append(f"   추천 대상은 {recommended_for}.")
    if cautions:
        lines.append(f"   주의할 점은 {cautions}.")

    if detail_level == "full":
        if detail_description:
            lines.append(f"   상세 설명을 자연스럽게 풀면 {detail_description}.")
        if review_summary:
            lines.append(f"   리뷰를 훑어보면 {review_summary}.")

    return "\n".join(lines)


def format_products_for_prompt(
    products: list[dict[str, Any]],
    detail_level: str = "full",
    max_count: int | None = None,
) -> str:
    selected = products[:max_count] if max_count else products
    if not selected:
        return "현재 조회된 상품 후보가 없습니다."
    return "\n\n".join(
        product_prompt_card(product, index, detail_level)
        for index, product in enumerate(selected, start=1)
    )


def build_prompt_with_products(
    template: str,
    fields: dict[str, Any],
    products: list[dict[str, Any]],
    settings: dict[str, Any] | None = None,
) -> str:
    budget = prompt_char_budget(settings)
    if not products:
        return render_prompt(template, {**fields, "products": format_products_for_prompt(products)})

    for detail_level in ("full", "balanced", "compact"):
        for max_count in range(len(products), 0, -1):
            product_text = format_products_for_prompt(products, detail_level, max_count)
            prompt = render_prompt(template, {**fields, "products": product_text})
            if len(prompt) <= budget:
                return prompt

    product_text = product_prompt_card(products[0], 1, "compact")
    note = (
        "상품 후보 설명이 길어져서, 컨텍스트 한도 안에서 가장 가까운 후보부터 담았습니다.\n\n"
    )
    return render_prompt(template, {**fields, "products": note + product_text})


def format_reviews_for_prompt(reviews: list[dict[str, Any]], max_chars: int) -> str:
    lines: list[str] = []
    for review in reviews:
        line = (
            f"- {review['user_name']}님은 평점 {review['rating']}점을 줬고, "
            f"리뷰 내용은 '{compact_prompt_text(review['content'], 260)}'입니다. "
            f"좋게 본 점은 {compact_prompt_text(review.get('pros'), 120) or '정보 없음'}, "
            f"아쉬운 점은 {compact_prompt_text(review.get('cons'), 120) or '정보 없음'}입니다."
        )
        next_text = "\n".join(lines + [line])
        if lines and len(next_text) > max_chars:
            lines.append("리뷰가 길어 컨텍스트 한도 안에서 앞쪽 리뷰까지만 담았습니다.")
            break
        lines.append(line)
    return "\n".join(lines)


def default_ai_settings() -> dict[str, Any]:
    return {
        "provider": normalize_ai_provider(AI_PROVIDER),
        "ollama_base_url": OLLAMA_BASE_URL,
        "ollama_model": OLLAMA_MODEL,
        "lmstudio_base_url": normalize_lmstudio_base_url(LMSTUDIO_BASE_URL),
        "lmstudio_model": LMSTUDIO_MODEL,
        "lmstudio_api_key": LMSTUDIO_API_KEY,
    }


def ensure_ai_settings_table() -> None:
    defaults = default_ai_settings()
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_settings (
                id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
                provider VARCHAR(30) NOT NULL DEFAULT 'ollama',
                ollama_base_url TEXT NOT NULL DEFAULT 'http://ollama:11434',
                ollama_model TEXT NOT NULL DEFAULT 'easypick-ai',
                lmstudio_base_url TEXT NOT NULL DEFAULT 'http://host.docker.internal:1234/v1',
                lmstudio_model TEXT NOT NULL DEFAULT 'local-model',
                lmstudio_api_key TEXT NOT NULL DEFAULT '',
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        conn.execute(
            """
            INSERT INTO ai_settings (
                id, provider, ollama_base_url, ollama_model,
                lmstudio_base_url, lmstudio_model, lmstudio_api_key
            )
            VALUES (1, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            [
                defaults["provider"],
                defaults["ollama_base_url"],
                defaults["ollama_model"],
                defaults["lmstudio_base_url"],
                defaults["lmstudio_model"],
                defaults["lmstudio_api_key"],
            ],
        )


def get_ai_settings() -> dict[str, Any]:
    ensure_ai_settings_table()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT provider, ollama_base_url, ollama_model,
                   lmstudio_base_url, lmstudio_model, lmstudio_api_key, updated_at
            FROM ai_settings
            WHERE id = 1
            """
        ).fetchone()
    settings = dict(row or default_ai_settings())
    settings["provider"] = normalize_ai_provider(settings.get("provider"))
    settings["ollama_base_url"] = trim_url(settings.get("ollama_base_url") or OLLAMA_BASE_URL)
    settings["lmstudio_base_url"] = normalize_lmstudio_base_url(
        settings.get("lmstudio_base_url") or LMSTUDIO_BASE_URL
    )
    settings["lmstudio_api_key"] = settings.get("lmstudio_api_key") or ""
    return settings


def save_ai_settings(request: AiSettingsRequest) -> dict[str, Any]:
    provider = normalize_ai_provider(request.provider)
    if provider not in {"ollama", "lmstudio"}:
        raise HTTPException(status_code=400, detail="provider는 ollama 또는 lmstudio여야 합니다.")

    ensure_ai_settings_table()
    with get_connection() as conn:
        row = conn.execute(
            """
            UPDATE ai_settings
            SET provider = %s,
                ollama_base_url = %s,
                ollama_model = %s,
                lmstudio_base_url = %s,
                lmstudio_model = %s,
                lmstudio_api_key = %s,
                updated_at = NOW()
            WHERE id = 1
            RETURNING provider, ollama_base_url, ollama_model,
                      lmstudio_base_url, lmstudio_model, lmstudio_api_key, updated_at
            """,
            [
                provider,
                trim_url(request.ollama_base_url),
                request.ollama_model.strip(),
                normalize_lmstudio_base_url(request.lmstudio_base_url),
                request.lmstudio_model.strip(),
                request.lmstudio_api_key or "",
            ],
        ).fetchone()
    return dict(row)


def lmstudio_headers(settings: dict[str, Any]) -> dict[str, str]:
    if settings.get("lmstudio_api_key"):
        return {"Authorization": f"Bearer {settings['lmstudio_api_key']}"}
    return {}


async def unload_ollama_model(settings: dict[str, Any], model: str | None = None) -> dict[str, Any]:
    target_model = model or settings["ollama_model"]
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.post(
                f"{settings['ollama_base_url']}/api/generate",
                json={"model": target_model, "prompt": "", "stream": False, "keep_alive": 0},
            )
            response.raise_for_status()
        return {"provider": "ollama", "model": target_model, "ok": True}
    except httpx.HTTPError as exc:
        return {
            "provider": "ollama",
            "model": target_model,
            "ok": False,
            "detail": str(exc),
        }


async def unload_lmstudio_model(settings: dict[str, Any], model: str | None = None) -> dict[str, Any]:
    target_model = model or settings["lmstudio_model"]
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            headers = lmstudio_headers(settings)
            root_url = lmstudio_root_url(settings["lmstudio_base_url"])
            models_response = await client.get(f"{root_url}/api/v1/models", headers=headers)
            models_response.raise_for_status()
            data = models_response.json()
            raw_models = data.get("models") or data.get("data") or []
            instance_ids: list[str] = []
            for item in raw_models:
                model_id = item.get("key") or item.get("id")
                loaded_instances = item.get("loaded_instances") or []
                loaded_ids = [
                    instance.get("id")
                    for instance in loaded_instances
                    if isinstance(instance, dict) and instance.get("id")
                ]
                if target_model == model_id:
                    instance_ids.extend(loaded_ids)
                elif target_model in loaded_ids:
                    instance_ids.append(target_model)

            if not instance_ids:
                return {
                    "provider": "lmstudio",
                    "model": target_model,
                    "ok": True,
                    "unloaded": 0,
                }

            for instance_id in dict.fromkeys(instance_ids):
                response = await client.post(
                    f"{root_url}/api/v1/models/unload",
                    json={"instance_id": instance_id},
                    headers=headers,
                )
                response.raise_for_status()
        return {
            "provider": "lmstudio",
            "model": target_model,
            "ok": True,
            "unloaded": len(dict.fromkeys(instance_ids)),
        }
    except httpx.HTTPError as exc:
        return {
            "provider": "lmstudio",
            "model": target_model,
            "ok": False,
            "detail": str(exc),
        }


async def unload_ai_provider(
    provider: str,
    settings: dict[str, Any],
    model: str | None = None,
) -> dict[str, Any]:
    selected_provider = normalize_ai_provider(provider)
    if selected_provider == "ollama":
        return await unload_ollama_model(settings, model)
    if selected_provider == "lmstudio":
        return await unload_lmstudio_model(settings, model)
    return {"provider": provider, "model": model, "ok": False, "detail": "Unknown provider."}


async def unload_lmstudio_other_models(
    settings: dict[str, Any],
    keep_model: str,
) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            headers = lmstudio_headers(settings)
            root_url = lmstudio_root_url(settings["lmstudio_base_url"])
            models_response = await client.get(f"{root_url}/api/v1/models", headers=headers)
            models_response.raise_for_status()
            data = models_response.json()
            raw_models = data.get("models") or data.get("data") or []
            instance_ids: list[str] = []
            for item in raw_models:
                model_id = item.get("key") or item.get("id")
                if model_id == keep_model:
                    continue
                loaded_instances = item.get("loaded_instances") or []
                instance_ids.extend(
                    instance.get("id")
                    for instance in loaded_instances
                    if isinstance(instance, dict) and instance.get("id")
                )

            for instance_id in dict.fromkeys(instance_ids):
                response = await client.post(
                    f"{root_url}/api/v1/models/unload",
                    json={"instance_id": instance_id},
                    headers=headers,
                )
                response.raise_for_status()
        return {
            "provider": "lmstudio",
            "model": keep_model,
            "ok": True,
            "unloaded": len(dict.fromkeys(instance_ids)),
        }
    except httpx.HTTPError as exc:
        return {
            "provider": "lmstudio",
            "model": keep_model,
            "ok": False,
            "detail": str(exc),
        }


async def ensure_lmstudio_model_loaded(settings: dict[str, Any]) -> None:
    headers = lmstudio_headers(settings)
    root_url = lmstudio_root_url(settings["lmstudio_base_url"])
    target_model = settings["lmstudio_model"]
    async with httpx.AsyncClient(timeout=90) as client:
        models_response = await client.get(f"{root_url}/api/v1/models", headers=headers)
        models_response.raise_for_status()
        data = models_response.json()
        raw_models = data.get("models") or data.get("data") or []
        for item in raw_models:
            model_id = item.get("key") or item.get("id")
            if model_id == target_model and item.get("loaded_instances"):
                return
        load_payload = {
            "model": target_model,
            "config": {"context_length": LMSTUDIO_CONTEXT_LENGTH},
        }
        load_response = await client.post(
            f"{root_url}/api/v1/models/load",
            json=load_payload,
            headers=headers,
        )
        if load_response.status_code in {400, 404, 422}:
            load_response = await client.post(
                f"{root_url}/api/v1/models/load",
                json={"model": target_model},
                headers=headers,
            )
        load_response.raise_for_status()


async def call_ollama(prompt: str, settings: dict[str, Any] | None = None) -> str:
    settings = settings or get_ai_settings()
    payload = {
        "model": settings["ollama_model"],
        "messages": [
            {"role": "system", "content": AI_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.2,
            "num_predict": AI_MAX_TOKENS,
            "num_ctx": OLLAMA_NUM_CTX,
        },
    }
    try:
        await unload_lmstudio_other_models(settings, keep_model="")
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(f"{settings['ollama_base_url']}/api/chat", json=payload)
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


async def call_lmstudio(
    prompt: str,
    settings: dict[str, Any] | None = None,
    max_tokens: int | None = None,
) -> str:
    settings = settings or get_ai_settings()
    payload = {
        "model": settings["lmstudio_model"],
        "messages": [
            {"role": "system", "content": AI_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": max_tokens or AI_MAX_TOKENS,
        "stream": False,
        "reasoning_effort": "none",
        "reasoning": {"effort": "none"},
    }
    headers = lmstudio_headers(settings)
    try:
        await unload_ai_provider("ollama", settings)
        await unload_lmstudio_other_models(settings, settings["lmstudio_model"])
        await ensure_lmstudio_model_loaded(settings)
        async with httpx.AsyncClient(timeout=LMSTUDIO_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{lmstudio_openai_url(settings['lmstudio_base_url'])}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            message = data["choices"][0]["message"]
            answer = message.get("content") or ""
            if not answer.strip() and message.get("reasoning_content"):
                retry_payload = {
                    **payload,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                f"{AI_SYSTEM_PROMPT} 내부 추론이나 Thinking Process를 쓰지 말고, "
                                "사용자에게 보여줄 최종 답변 본문만 바로 작성한다."
                            ),
                        },
                        {
                            "role": "user",
                            "content": (
                                "아래 요청에 대해 내부 추론 없이 최종 답변만 한국어로 작성하세요.\n\n"
                                f"{prompt}"
                            ),
                        },
                    ],
                }
                retry_response = await client.post(
                    f"{lmstudio_openai_url(settings['lmstudio_base_url'])}/chat/completions",
                    json=retry_payload,
                    headers=headers,
                )
                retry_response.raise_for_status()
                retry_data = retry_response.json()
                answer = retry_data["choices"][0]["message"].get("content") or ""
    except (httpx.HTTPError, KeyError, IndexError, TypeError):
        return (
            "AI 서버에 연결하지 못했습니다. LM Studio에서 Local Server를 켜고 "
            "모델이 로드되어 있는지 확인해 주세요."
        )
    return clean_ai_answer(answer)


async def call_ai(prompt: str) -> str:
    settings = get_ai_settings()
    if settings["provider"] == "lmstudio":
        return await call_lmstudio(prompt, settings)
    if settings["provider"] == "ollama":
        return await call_ollama(prompt, settings)
    return "AI_PROVIDER는 ollama 또는 lmstudio 중 하나로 설정해 주세요."


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
    settings = get_ai_settings()
    if settings["provider"] == "lmstudio":
        ai_model = settings["lmstudio_model"]
    else:
        ai_model = settings["ollama_model"]
    return {"status": "ok", "ai_provider": settings["provider"], "ai_model": ai_model}


@app.get("/api/admin/ai-settings")
def admin_get_ai_settings():
    return get_ai_settings()


@app.put("/api/admin/ai-settings")
def admin_update_ai_settings(request: AiSettingsRequest):
    return save_ai_settings(request)


@app.get("/api/admin/ai-settings/models")
async def admin_list_ai_models(
    provider: str = "ollama",
    base_url: str | None = None,
    api_key: str | None = None,
):
    selected_provider = normalize_ai_provider(provider)
    settings = get_ai_settings()
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(timeout=12) as client:
            if selected_provider == "ollama":
                url = trim_url(base_url or settings["ollama_base_url"])
                response = await client.get(f"{url}/api/tags")
                response.raise_for_status()
                data = response.json()
                models = [
                    {
                        "id": item.get("name"),
                        "name": item.get("name"),
                        "state": "available",
                        "details": item.get("details") or {},
                    }
                    for item in data.get("models", [])
                    if item.get("name")
                ]
                return {"provider": "ollama", "models": models}

            if selected_provider == "lmstudio":
                url = lmstudio_root_url(base_url or settings["lmstudio_base_url"])
                response = await client.get(f"{url}/api/v1/models", headers=headers)
                if response.status_code == 404:
                    response = await client.get(f"{lmstudio_openai_url(url)}/models", headers=headers)
                response.raise_for_status()
                data = response.json()
                raw_models = data.get("models") or data.get("data") or []
                models = []
                for item in raw_models:
                    model_id = item.get("key") or item.get("id")
                    model_type = item.get("type")
                    if model_id and model_type != "embedding":
                        loaded_instances = item.get("loaded_instances") or []
                        models.append(
                            {
                                "id": model_id,
                                "name": item.get("display_name") or model_id,
                                "state": "loaded" if loaded_instances else item.get("state", "available"),
                                "details": {
                                    "architecture": item.get("architecture") or item.get("arch"),
                                    "params": item.get("params_string"),
                                    "quantization": (item.get("quantization") or {}).get("name")
                                    if isinstance(item.get("quantization"), dict)
                                    else item.get("quantization"),
                                    "max_context_length": item.get("max_context_length"),
                                },
                            }
                        )
                return {"provider": "lmstudio", "models": models}
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="AI 서버에 연결하지 못했습니다. 주소와 서버 실행 상태를 확인해 주세요.",
        ) from exc

    raise HTTPException(status_code=400, detail="provider는 ollama 또는 lmstudio여야 합니다.")


@app.post("/api/admin/ai-settings/test")
async def admin_test_ai_settings(request: AiSettingsRequest):
    settings = {
        "provider": normalize_ai_provider(request.provider),
        "ollama_base_url": trim_url(request.ollama_base_url),
        "ollama_model": request.ollama_model.strip(),
        "lmstudio_base_url": normalize_lmstudio_base_url(request.lmstudio_base_url),
        "lmstudio_model": request.lmstudio_model.strip(),
        "lmstudio_api_key": request.lmstudio_api_key or "",
    }
    prompt = "한국어로 '연결 정상'이라고만 답해줘."
    if settings["provider"] == "lmstudio":
        answer = await call_lmstudio(prompt, settings, max_tokens=24)
    elif settings["provider"] == "ollama":
        answer = await call_ollama(prompt, settings)
    else:
        raise HTTPException(status_code=400, detail="provider는 ollama 또는 lmstudio여야 합니다.")
    if answer.startswith("AI 서버에 연결하지 못했습니다"):
        raise HTTPException(status_code=502, detail=answer)
    return {"ok": True, "answer": "연결 정상"}


@app.post("/api/admin/ai-settings/unload")
async def admin_unload_ai_model(request: AiUnloadRequest):
    settings = get_ai_settings()
    result = await unload_ai_provider(request.provider, settings, request.model)
    return result


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
                short_description, detail_description, recommended_for, cautions,
                specs, rating, review_count, stock
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                request.detail_description,
                request.recommended_for,
                request.cautions,
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
                detail_description = %s,
                recommended_for = %s,
                cautions = %s,
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
                request.detail_description,
                request.recommended_for,
                request.cautions,
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
    session_id = request.session_id or request.sessionId
    category = detect_category(request.message)
    min_price, max_price = parse_price(request.message)
    requested_count = parse_requested_count(request.message)
    usage_context = extract_usage_context(request.message)
    cart = get_cart_data(session_id) if session_id else None
    orders = get_orders_for_session(session_id) if session_id else []
    user_context = build_user_context(cart, orders)

    direct_context_answer = build_cart_order_direct_response(request.message, session_id)
    if direct_context_answer:
        return {
            "answer": direct_context_answer["answer"],
            "products": direct_context_answer["products"],
            "filters": {
                "category": category,
                "minPrice": min_price,
                "maxPrice": max_price,
                "requestedCount": requested_count,
                "usageContext": usage_context,
                "sessionContext": True,
            },
        }

    shopping_intent = is_shopping_intent(request.message, category, min_price, max_price)
    cart_order_intent = is_cart_order_intent(request.message)
    candidate_context = "사용자 조건에 맞춰 후보를 조회했습니다."
    if not shopping_intent and not cart_order_intent:
        candidates = []
        candidate_context = (
            "사용자가 아직 상품 카테고리, 예산, 용도 같은 쇼핑 조건을 말하지 않았습니다. "
            "이 경우 특정 상품을 추천하지 말고, 사용자의 말을 짧고 자연스럽게 받아준 뒤 "
            "원하는 상품 종류나 예산을 물어보세요."
        )
    elif cart_order_intent and cart and cart.get("items") and not category:
        candidates = cart_products_for_response(cart)[:10]
        candidate_context = "장바구니 상품을 중심으로 후보를 제공했습니다."
    else:
        candidates = search_products(
            query=None if category or min_price is not None or max_price is not None else request.message,
            category=category,
            min_price=min_price,
            max_price=max_price,
            sort="rating",
            limit=10,
        )

    if shopping_intent and not candidates:
        if category:
            candidates = search_products(category=category, sort="rating", limit=10)
            candidate_context = (
                "요청한 가격이나 세부 조건에 딱 맞는 상품은 찾지 못해, "
                "같은 카테고리 안에서 가까운 후보를 넓게 제공했습니다."
            )
        elif min_price is not None or max_price is not None:
            candidates = search_products(
                min_price=min_price,
                max_price=max_price,
                sort="rating",
                limit=10,
            )
            candidate_context = (
                "카테고리가 명확하지 않아 가격 조건에 맞는 후보를 넓게 제공했습니다."
            )
        else:
            candidates = []

    if shopping_intent and not candidates:
        candidates = search_products(sort="rating", limit=8)
        candidate_context = (
            "사용자 질문이 특정 상품 조건으로 정확히 매칭되지 않았거나 쇼핑과 직접 관련이 적어, "
            "EasyPick의 대표 후보를 제공했습니다. 답변에서는 질문을 자연스럽게 받아주고 "
            "EasyPick에서 도와줄 수 있는 쇼핑 탐색으로 연결하세요."
        )

    template = read_prompt(
        "recommend_prompt.txt",
        "사용자 질문:\n{message}\n\n요청 추천 개수:\n{requested_count}\n\n사용 목적/선호 조건:\n{usage_context}\n\n후보 선택 상황:\n{candidate_context}\n\n상품 후보:\n{products}\n\n반드시 한국어로 답변하세요.",
    )
    settings = get_ai_settings()
    prompt_candidate_count = requested_count or 3
    prompt_candidate_count = max(1, min(prompt_candidate_count, 5))
    prompt_candidates = candidates[:prompt_candidate_count]
    prompt = build_prompt_with_products(
        template,
        {
            "message": request.message,
            "requested_count": f"{requested_count}개"
            if requested_count
            else "사용자가 지정하지 않음. 기본 3개 이하로 선별",
            "usage_context": usage_context or "명확히 제공되지 않음",
            "candidate_context": candidate_context,
            "user_context": user_context,
        },
        prompt_candidates,
        settings,
    )
    answer = await call_ai(prompt)
    product_ids = [product["id"] for product in candidates]
    save_ai_log(request.message, answer, product_ids)
    return {
        "answer": answer,
        "products": candidates,
        "filters": {
            "category": category,
            "minPrice": min_price,
            "maxPrice": max_price,
            "requestedCount": requested_count,
            "usageContext": usage_context,
        },
    }


@app.post("/api/ai/compare")
async def ai_compare(request: CompareRequest):
    products = get_products_by_ids(request.product_ids)
    if len(products) < 2:
        return {"answer": "상품이 2개 이상 선택되어야 비교할 수 있습니다.", "products": products}

    categories = sorted({product.get("category") or "카테고리 없음" for product in products})
    if len(categories) > 1:
        return {
            "answer": (
                "선택한 상품의 카테고리가 서로 달라 AI 비교 설명을 만들지 않았습니다.\n"
                f"- 선택된 카테고리: {', '.join(categories)}\n"
                "- 노트북과 모니터처럼 용도와 스펙 기준이 다른 상품은 가격만으로 비교하면 결론이 왜곡될 수 있습니다.\n"
                "- 같은 카테고리 상품 2개 이상을 선택해 주세요."
            ),
            "products": products,
        }

    template = read_prompt(
        "compare_prompt.txt",
        "사용자 비교 기준:\n{criteria}\n\n비교 상품:\n{products}\n\n한국어로 답변하세요.",
    )
    settings = get_ai_settings()
    prompt = build_prompt_with_products(
        template,
        {"criteria": request.criteria or "가격, 스펙, 평점, 리뷰 기준으로 비교"},
        products,
        settings,
    )
    answer = await call_ai(prompt)
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

    template = read_prompt(
        "review_summary_prompt.txt",
        "상품명:\n{product_name}\n\n리뷰:\n{reviews}\n\n한국어로 요약하세요.",
    )
    settings = get_ai_settings()
    budget = prompt_char_budget(settings)
    base_prompt = render_prompt(template, {"product_name": product["name"], "reviews": ""})
    review_budget = max(1200, budget - len(base_prompt))
    review_lines = format_reviews_for_prompt(reviews, review_budget)
    prompt = render_prompt(template, {"product_name": product["name"], "reviews": review_lines})
    answer = await call_ai(prompt)
    save_ai_log(f"리뷰 요약: {product['name']}", answer, [product["id"]])
    return {"answer": answer, "product": product}

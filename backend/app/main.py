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
    session_id: str | None = None
    sessionId: str | None = None


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
        "공통 답변 지시:\n"
        "- 사고 과정, 추론 과정, 내부 검토 내용은 출력하지 마세요.\n"
        "- 최종 답변만 한국어로 작성하세요.\n"
        "- 상품명과 브랜드명을 제외한 모든 설명은 한국어로만 작성하세요.\n"
        "- 제공된 상품 후보에 없는 상품명, 가격, 스펙, 평점, 리뷰, 배송, 할인 정보는 절대 쓰지 마세요.\n"
        "- 말투는 자연스러운 쇼핑 상담원처럼 하되, 광고처럼 과장하지 마세요.\n"
        "- 사용자가 요청한 추천 개수와 조건을 우선 지키세요.\n"
        "- 후보 상품은 참고 자료입니다. 모든 후보를 소개하지 말고 조건에 맞는 상품만 선별하세요.\n"
        "- 정보가 부족한 항목은 추측하지 말고 '제공된 정보만으로는 확인하기 어렵습니다'라고 말하세요.\n\n"
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


def format_products_for_prompt(products: list[dict[str, Any]]) -> str:
    lines = []
    for index, product in enumerate(products, start=1):
        specs = format_specs(product["specs"])
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
                    "상품 후보에 없는 정보는 만들지 않는다. "
                    "후보 전체를 나열하지 말고 사용자 조건에 맞는 상품만 선별한다. "
                    "사용자가 요청한 추천 개수를 반드시 지킨다. "
                    "스펙 키나 값이 영어로 제공되어도 설명 문장은 한국어로 작성한다. "
                    "영어 문장으로 답하지 않는다."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 700,
            "num_ctx": 8192,
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
    english_markers = [
        "okay,",
        "let's",
        "the user",
        "we need",
        "first,",
        "so,",
        "here",
        "based on",
        "recommend",
        "comparison",
        "summary",
    ]
    if lowered.startswith(tuple(english_markers)):
        return True
    korean_chars = len(re.findall(r"[가-힣]", answer))
    latin_chars = len(re.findall(r"[A-Za-z]", answer))
    english_words = re.findall(
        r"\b(the|and|or|is|are|this|that|with|for|because|price|review|rating|product|recommend|compare|user|based|summary|pros|cons)\b",
        lowered,
    )
    if len(english_words) >= 4:
        return True
    return korean_chars < 40 and latin_chars > korean_chars


def fallback_recommendation(
    products: list[dict[str, Any]],
    user_message: str,
    requested_count: int | None = None,
    usage_context: str | None = None,
) -> str:
    count = requested_count or 3
    count = max(1, min(count, len(products), 5))
    top_products = products[:count]
    lines = [
        f"요청하신 조건에 맞춰 {count}개를 골랐습니다.",
        "",
        "추천 상품",
    ]
    for index, product in enumerate(top_products, start=1):
        specs = format_specs(product["specs"])
        lines.extend(
            [
                f"{index}. {product['name']}",
                f"   - 가격: {product['price']:,}원",
                f"   - 추천 이유: 평점 {product['rating']}점, 리뷰 {product['review_count']}개, 주요 스펙({specs})을 기준으로 조건에 잘 맞습니다.",
                f"   - 장점: {product['short_description']}",
                "   - 아쉬운 점: 제공된 정보만으로는 장기 내구성이나 실제 배송 만족도는 확인하기 어렵습니다.",
                "   - 구매 전 확인할 점: 실제 사용 공간, 필요한 기능, 소음과 무게 조건을 확인하세요.",
            ]
        )
        if usage_context:
            lines.append(f"   - 사용 목적 적합성: '{usage_context}' 조건을 우선 고려했습니다.")
        lines.append("")
    lines.extend(
        [
            "최종 한 줄 추천",
            f"- '{user_message}' 조건에서는 {top_products[0]['name']}를 먼저 확인하는 것이 좋습니다.",
        ]
    )
    return "\n".join(lines)


def wants_price_only(criteria: str | None) -> bool:
    text = (criteria or "").replace(" ", "")
    return "가격" in text and any(word in text for word in ["만", "싼", "최저", "저렴"])


def wants_beginner_explanation(criteria: str | None) -> bool:
    text = criteria or ""
    beginner_words = ["몰라", "모르", "쉽게", "초보", "지식", "설명", "비교설명", "알려"]
    return any(word in text for word in beginner_words)


def parse_refresh_rate(value: Any) -> int:
    match = re.search(r"(\d+)", str(value or ""))
    return int(match.group(1)) if match else 0


def spec_summary(product: dict[str, Any]) -> str:
    specs = product.get("specs") or {}
    category = product.get("category")
    if category == "모니터":
        keys = ["Size", "Resolution", "RefreshRate", "Panel", "Ratio", "Color"]
    elif category == "노트북":
        keys = ["CPU", "GPU", "RAM", "Storage", "Display", "Weight", "RefreshRate"]
    elif category == "무선청소기":
        keys = ["Suction", "Runtime", "Weight", "Filter", "Dustbin"]
    elif category == "공기청정기":
        keys = ["Coverage", "Filter", "Sensor", "Noise", "Mode"]
    else:
        keys = list(specs.keys())[:5]
    parts = [humanize_spec(key, specs[key]) for key in keys if specs.get(key)]
    return ", ".join(parts) if parts else "제공된 핵심 스펙이 많지 않습니다"


def beginner_spec_notes(products: list[dict[str, Any]]) -> list[str]:
    keys = {key for product in products for key in (product.get("specs") or {}).keys()}
    notes: list[str] = []
    if "RefreshRate" in keys:
        notes.append("주사율(RefreshRate)은 화면이 1초에 몇 번 새로 그려지는지 보는 숫자입니다. 높을수록 움직임이 더 부드럽게 보일 수 있어 게임이나 빠른 화면에서 체감이 납니다.")
    if "Resolution" in keys:
        notes.append("해상도(Resolution)는 화면이 얼마나 촘촘하게 보이는지에 가깝습니다. QHD, 4K처럼 올라갈수록 글자와 이미지가 더 세밀하게 보일 수 있습니다.")
    if "Panel" in keys:
        notes.append("패널(Panel)은 화면의 색감, 명암, 시야각에 영향을 주는 방식입니다. IPS는 색감과 시야각, VA는 명암비 쪽을 볼 때 자주 비교합니다.")
    if "Ratio" in keys:
        notes.append("화면 비율(Ratio)은 화면의 가로세로 형태입니다. 21:9처럼 넓은 화면은 여러 창을 나란히 띄우는 작업에 유리할 수 있습니다.")
    if "Color" in keys:
        notes.append("색 영역(Color)은 색을 얼마나 넓게 표현하는지 보는 기준입니다. 디자인이나 색 보정 작업에서는 참고할 만합니다.")
    if "CPU" in keys:
        notes.append("CPU는 노트북의 두뇌처럼 전체 작업을 처리하는 부품입니다.")
    if "GPU" in keys:
        notes.append("GPU는 게임 화면이나 그래픽 작업을 처리하는 부품입니다.")
    if "RAM" in keys:
        notes.append("RAM은 책상 넓이처럼 여러 작업을 동시에 펼쳐두는 여유 공간에 가깝습니다.")
    return notes[:5]


def fallback_compare(products: list[dict[str, Any]], criteria: str | None) -> str:
    categories = sorted({product.get("category") or "카테고리 없음" for product in products})
    criteria_text = criteria or "가격, 스펙, 평점, 리뷰 기준으로 비교"
    if len(categories) > 1:
        return (
            "이 조합은 바로 순위를 매기기 어렵습니다.\n"
            f"선택된 카테고리가 {', '.join(categories)}로 서로 달라요. 노트북과 모니터처럼 쓰임새가 다른 상품은 가격이나 스펙 숫자만 놓고 '이게 더 좋다'고 말하면 결론이 이상해질 수 있습니다.\n\n"
            "같은 카테고리 상품끼리 선택하면 가격, 스펙, 평점, 리뷰를 훨씬 자연스럽게 비교해드릴 수 있습니다."
        )

    sorted_by_price = sorted(products, key=lambda item: item["price"])
    cheapest = sorted_by_price[0]
    highest_rating = max(products, key=lambda item: item["rating"])
    category = categories[0]

    if wants_price_only(criteria):
        lines = [
            f"{category} 상품을 가격 기준으로만 보면 이렇게 정리됩니다.",
            "",
            "| 순위 | 상품 | 가격 | 차이 |",
            "| --- | --- | ---: | --- |",
        ]
        for index, product in enumerate(sorted_by_price, start=1):
            gap = product["price"] - cheapest["price"]
            gap_text = "최저가" if gap == 0 else f"최저가보다 {gap:,}원 높음"
            lines.append(f"| {index} | {product['name']} | {product['price']:,}원 | {gap_text} |")
        lines.extend(
            [
                "",
                f"가격만 보면 {cheapest['name']}가 가장 부담이 적습니다.",
                "다만 가격만으로는 화면 품질, 부드러움, 사용 목적 적합성까지 판단하기 어렵습니다. 가격 비교만 원하셨으니 여기서는 다른 기준으로 순위를 바꾸지는 않겠습니다.",
            ]
        )
        return "\n".join(lines)

    lines = [
        f"{category} {len(products)}개를 비교해볼게요.",
    ]
    if wants_beginner_explanation(criteria):
        lines.append("스펙 용어가 낯설 수 있으니, 먼저 어려운 말부터 쉽게 풀어서 볼게요.")
        notes = beginner_spec_notes(products)
        if notes:
            lines.extend(["", "스펙을 쉽게 보면"])
            lines.extend(f"- {note}" for note in notes)

    lines.extend(
        [
            "",
            "한눈에 비교하면",
            "| 상품 | 가격 | 핵심 스펙 | 평점/리뷰 |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for product in products:
        lines.append(
            f"| {product['name']} | {product['price']:,}원 | {spec_summary(product)} | "
            f"{product['rating']}점 / 리뷰 {product['review_count']}개 |"
        )

    lines.extend(["", "상품별로 쉽게 말하면"])
    for product in products:
        lines.append(
            f"- {product['name']}: {product['price']:,}원이고, 핵심 스펙은 {spec_summary(product)}입니다. "
            f"평점은 {product['rating']}점, 리뷰는 {product['review_count']}개라서 이 정도 사용자 반응이 쌓여 있습니다."
        )

    lines.extend(["", "기준별로 보면"])
    lines.append(f"- 가격 부담을 가장 줄이고 싶다면 {cheapest['name']}가 먼저 보입니다.")
    if category == "모니터":
        refresh_candidates = [
            product for product in products if (product.get("specs") or {}).get("RefreshRate")
        ]
        if refresh_candidates:
            smoothest = max(refresh_candidates, key=lambda item: parse_refresh_rate((item.get("specs") or {}).get("RefreshRate")))
            lines.append(f"- 화면 움직임의 부드러움을 중시하면 주사율이 높은 {smoothest['name']}를 먼저 볼 만합니다.")
        resolution_priority = {"4K UHD": 4, "UWQHD": 3, "QHD": 2, "FHD": 1}
        resolution_candidates = [
            product for product in products if (product.get("specs") or {}).get("Resolution")
        ]
        if resolution_candidates:
            sharpest = max(
                resolution_candidates,
                key=lambda item: resolution_priority.get(str((item.get("specs") or {}).get("Resolution")), 0),
            )
            lines.append(f"- 선명도나 작업 공간을 중시하면 해상도 기준으로 {sharpest['name']}도 확인할 만합니다.")
    lines.append(f"- 평점만 보면 {highest_rating['name']}가 가장 높지만, 평점 차이가 작다면 가격과 스펙을 같이 보는 편이 좋습니다.")
    lines.extend(
        [
            "",
            "최종적으로는",
            f"- 가격과 무난한 만족도를 같이 보면 {cheapest['name']}를 먼저 확인해볼 만합니다."
            if cheapest == highest_rating
            else f"- 가격을 중시하면 {cheapest['name']}, 사용자 반응을 중시하면 {highest_rating['name']} 쪽을 먼저 비교해보면 됩니다.",
            "- 제공된 정보 외 배송, 할인, AS, 장기 내구성은 확인하기 어렵습니다.",
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

    if not is_shopping_intent(request.message, category, min_price, max_price):
        return {
            "answer": "어떤 상품을 찾으시는지 예산, 용도, 카테고리를 알려주시면 EasyPick DB 상품 안에서만 추천해드릴게요.",
            "products": [],
            "filters": {
                "category": category,
                "minPrice": min_price,
                "maxPrice": max_price,
                "requestedCount": requested_count,
                "usageContext": usage_context,
            },
        }

    if is_cart_order_intent(request.message) and cart and cart.get("items") and not category:
        candidates = cart_products_for_response(cart)[:10]
    else:
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
            "filters": {
                "category": category,
                "minPrice": min_price,
                "maxPrice": max_price,
                "requestedCount": requested_count,
                "usageContext": usage_context,
            },
        }

    template = read_prompt(
        "recommend_prompt.txt",
        "사용자 질문:\n{message}\n\n요청 추천 개수:\n{requested_count}\n\n사용 목적/선호 조건:\n{usage_context}\n\n상품 후보:\n{products}\n\n반드시 한국어로 답변하세요.",
    )
    prompt = final_answer_instructions() + template.format(
        message=request.message,
        requested_count=f"{requested_count}개" if requested_count else "사용자가 지정하지 않음. 기본 3개 이하로 선별",
        usage_context=usage_context or "명확히 제공되지 않음",
        user_context=user_context,
        products=format_products_for_prompt(candidates),
    )
    answer = await call_ollama(prompt)
    if needs_korean_fallback(answer):
        answer = fallback_recommendation(candidates, request.message, requested_count, usage_context)
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

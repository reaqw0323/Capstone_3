const priceFormatter = new Intl.NumberFormat("ko-KR");

export default function ProductCompareTable({ products }) {
  if (!products.length) {
    return <p className="empty-text">비교할 상품을 선택해 주세요.</p>;
  }

  const specKeys = Array.from(new Set(products.flatMap((product) => Object.keys(product.specs || {}))));

  const minPrice = Math.min(...products.map((p) => p.price));
  const maxRating = Math.max(...products.map((p) => p.rating));

  return (
    <div className="table-scroll">
      <table className="compare-table">
        <thead>
          <tr>
            <th>항목</th>
            {products.map((product) => (
              <th key={product.id}>
                {product.name}
                {product.price === minPrice && (
                  <span className="badge badge-lowest" style={{ marginLeft: 6 }}>최저가</span>
                )}
                {product.rating === maxRating && (
                  <span className="badge badge-top-rated" style={{ marginLeft: 6 }}>평점 우수</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>이미지</td>
            {products.map((product) => (
              <td key={product.id}>
                <img className="compare-image" src={product.image_url} alt={product.name} />
              </td>
            ))}
          </tr>
          <tr>
            <td>브랜드</td>
            {products.map((product) => (
              <td key={product.id}>{product.brand}</td>
            ))}
          </tr>
          <tr>
            <td>가격</td>
            {products.map((product) => (
              <td key={product.id} className={product.price === minPrice ? "cell-best-price" : ""}>
                {priceFormatter.format(product.price)}원
                {product.price === minPrice && (
                  <span className="badge badge-lowest" style={{ marginLeft: 6 }}>최저가</span>
                )}
              </td>
            ))}
          </tr>
          <tr>
            <td>평점</td>
            {products.map((product) => (
              <td key={product.id} className={product.rating === maxRating ? "cell-best-rating" : ""}>
                {product.rating}점
                {product.rating === maxRating && (
                  <span className="badge badge-top-rated" style={{ marginLeft: 6 }}>평점 우수</span>
                )}
              </td>
            ))}
          </tr>
          <tr>
            <td>리뷰 수</td>
            {products.map((product) => (
              <td key={product.id}>{product.review_count}개</td>
            ))}
          </tr>
          {specKeys.map((key) => {
            const values = products.map((p) => p.specs?.[key] || "");
            const allSame = values.every((v) => v === values[0]);
            return (
              <tr key={key} className={!allSame ? "spec-row-diff" : ""}>
                <td>{key}</td>
                {products.map((product) => (
                  <td key={product.id}>{product.specs?.[key] || "정보 없음"}</td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

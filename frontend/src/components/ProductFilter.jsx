export default function ProductFilter({ categories, filters, onChange, onSubmit }) {
  const update = (key, value) => onChange({ ...filters, [key]: value });

  return (
    <form className="filter-panel" onSubmit={onSubmit}>
      <label>
        검색어
        <input
          value={filters.query || ""}
          onChange={(event) => update("query", event.target.value)}
          placeholder="무선청소기, 게임용 모니터..."
        />
      </label>
      <label>
        카테고리
        <select
          value={filters.category || ""}
          onChange={(event) => update("category", event.target.value)}
        >
          <option value="">전체</option>
          {categories.map((category) => (
            <option key={category.id} value={category.name}>
              {category.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        최저가
        <input
          type="number"
          min="0"
          value={filters.minPrice || ""}
          onChange={(event) => update("minPrice", event.target.value)}
          placeholder="0"
        />
      </label>
      <label>
        최고가
        <input
          type="number"
          min="0"
          value={filters.maxPrice || ""}
          onChange={(event) => update("maxPrice", event.target.value)}
          placeholder="200000"
        />
      </label>
      <label>
        브랜드
        <input
          value={filters.brand || ""}
          onChange={(event) => update("brand", event.target.value)}
          placeholder="NovaTech"
        />
      </label>
      <label>
        정렬
        <select value={filters.sort || "rating"} onChange={(event) => update("sort", event.target.value)}>
          <option value="rating">평점순</option>
          <option value="price_asc">낮은 가격순</option>
          <option value="price_desc">높은 가격순</option>
          <option value="review">리뷰 많은순</option>
          <option value="new">최신순</option>
        </select>
      </label>
      <button className="button primary filter-button" type="submit">
        필터 적용
      </button>
    </form>
  );
}

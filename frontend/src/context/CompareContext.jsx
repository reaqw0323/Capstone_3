import { createContext, useContext, useEffect, useMemo, useState } from "react";

const CompareContext = createContext(null);
const STORAGE_KEY = "easypick_compare_ids";

export function CompareProvider({ children }) {
  const [compareIds, setCompareIds] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(compareIds));
  }, [compareIds]);

  const value = useMemo(() => {
    const toggleCompare = (id) => {
      setCompareIds((current) => {
        if (current.includes(id)) {
          return current.filter((item) => item !== id);
        }
        return [...current, id].slice(-4);
      });
    };

    const clearCompare = () => setCompareIds([]);

    return { compareIds, toggleCompare, clearCompare };
  }, [compareIds]);

  return <CompareContext.Provider value={value}>{children}</CompareContext.Provider>;
}

export function useCompare() {
  const context = useContext(CompareContext);
  if (!context) {
    throw new Error("useCompare는 CompareProvider 안에서 사용해야 합니다.");
  }
  return context;
}

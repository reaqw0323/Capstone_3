import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { requestAiCompare, requestRecommendation, requestReviewSummary } from "../api/ai";

const AiStateContext = createContext(null);
const STORAGE_KEY = "easypick_ai_state_v1";

const idleCompareTask = {
  id: "",
  status: "idle",
  productIds: [],
  criteria: "",
  answer: "",
  error: "",
};

function createId(prefix) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function sameIds(left = [], right = []) {
  return left.length === right.length && left.every((id, index) => Number(id) === Number(right[index]));
}

function normalizeStoredTask(task) {
  if (!task) return null;
  if (task.status === "loading") {
    return {
      ...task,
      status: "error",
      error: "새로고침으로 생성이 중단되었습니다. 다시 요청해 주세요.",
    };
  }
  return task;
}

function readStoredState() {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
    const reviewSummaries = Object.fromEntries(
      Object.entries(stored.reviewSummaries || {}).map(([productId, task]) => [
        productId,
        normalizeStoredTask(task),
      ])
    );

    return {
      assistantHistory: (stored.assistantHistory || [])
        .map(normalizeStoredTask)
        .filter(Boolean)
        .slice(0, 5),
      compareTask: normalizeStoredTask(stored.compareTask) || idleCompareTask,
      reviewSummaries,
    };
  } catch {
    return {
      assistantHistory: [],
      compareTask: idleCompareTask,
      reviewSummaries: {},
    };
  }
}

export function AiStateProvider({ children }) {
  const storedState = useMemo(readStoredState, []);
  const [assistantHistory, setAssistantHistory] = useState(storedState.assistantHistory);
  const [compareTask, setCompareTask] = useState(storedState.compareTask);
  const [reviewSummaries, setReviewSummaries] = useState(storedState.reviewSummaries);

  useEffect(() => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        assistantHistory,
        compareTask,
        reviewSummaries,
      })
    );
  }, [assistantHistory, compareTask, reviewSummaries]);

  const value = useMemo(() => {
    const assistantLoading = assistantHistory.some((item) => item.status === "loading");

    const askAssistant = async (message, sessionId) => {
      const question = message.trim();
      if (!question || assistantLoading) return;

      const taskId = createId("assistant");
      const pendingItem = {
        id: taskId,
        status: "loading",
        question,
        answer: "",
        products: [],
        error: "",
        createdAt: new Date().toISOString(),
      };

      setAssistantHistory((current) => [pendingItem, ...current].slice(0, 5));

      try {
        const result = await requestRecommendation(question, sessionId);
        setAssistantHistory((current) =>
          current.map((item) =>
            item.id === taskId
              ? {
                  ...item,
                  status: "done",
                  answer: result.answer,
                  products: result.products || [],
                  completedAt: new Date().toISOString(),
                }
              : item
          )
        );
      } catch {
        setAssistantHistory((current) =>
          current.map((item) =>
            item.id === taskId
              ? {
                  ...item,
                  status: "error",
                  error: "AI 추천 요청 중 오류가 발생했습니다. 백엔드와 AI 서버 상태를 확인해 주세요.",
                }
              : item
          )
        );
      }
    };

    const clearAssistantHistory = () => setAssistantHistory([]);

    const startCompare = async (productIds, criteria) => {
      const ids = productIds.map(Number);
      if (ids.length < 2 || compareTask.status === "loading") return;

      const taskId = createId("compare");
      setCompareTask({
        id: taskId,
        status: "loading",
        productIds: ids,
        criteria,
        answer: "",
        error: "",
        startedAt: new Date().toISOString(),
      });

      try {
        const result = await requestAiCompare(ids, criteria);
        setCompareTask((current) =>
          current.id === taskId
            ? {
                ...current,
                status: "done",
                answer: result.answer,
                completedAt: new Date().toISOString(),
              }
            : current
        );
      } catch {
        setCompareTask((current) =>
          current.id === taskId
            ? {
                ...current,
                status: "error",
                error: "AI 비교 설명 생성 중 오류가 발생했습니다.",
              }
            : current
        );
      }
    };

    const startReviewSummary = async (productId) => {
      const key = String(productId);
      const currentTask = reviewSummaries[key];
      if (currentTask?.status === "loading") return;

      const taskId = createId(`review-${key}`);
      setReviewSummaries((current) => ({
        ...current,
        [key]: {
          id: taskId,
          status: "loading",
          productId: Number(productId),
          answer: "",
          error: "",
          startedAt: new Date().toISOString(),
        },
      }));

      try {
        const result = await requestReviewSummary(productId);
        setReviewSummaries((current) => {
          if (current[key]?.id !== taskId) return current;
          return {
            ...current,
            [key]: {
              ...current[key],
              status: "done",
              answer: result.answer,
              completedAt: new Date().toISOString(),
            },
          };
        });
      } catch {
        setReviewSummaries((current) => {
          if (current[key]?.id !== taskId) return current;
          return {
            ...current,
            [key]: {
              ...current[key],
              status: "error",
              error: "AI 리뷰 요약 생성 중 오류가 발생했습니다.",
            },
          };
        });
      }
    };

    const compareMatches = (productIds) => sameIds(compareTask.productIds, productIds.map(Number));

    return {
      assistantHistory,
      assistantLoading,
      askAssistant,
      clearAssistantHistory,
      compareTask,
      compareMatches,
      startCompare,
      reviewSummaries,
      startReviewSummary,
    };
  }, [assistantHistory, compareTask, reviewSummaries]);

  return <AiStateContext.Provider value={value}>{children}</AiStateContext.Provider>;
}

export function useAiState() {
  const context = useContext(AiStateContext);
  if (!context) {
    throw new Error("useAiState는 AiStateProvider 안에서 사용해야 합니다.");
  }
  return context;
}

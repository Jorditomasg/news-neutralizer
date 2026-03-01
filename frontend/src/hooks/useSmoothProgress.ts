import { useState, useEffect } from "react";

type TaskState = {
    backendProgress: number;
    status: string;
    displayProgress: number;
    expectedDurationMs: number;
    subscribers: Set<(val: number) => void>;
};

const tasksMap = new Map<string, TaskState>();
let ticker: NodeJS.Timeout | null = null;
const lastSaveMap = new Map<string, number>();

function saveTaskProgress(id: string, displayProgress: number) {
    if (typeof window === "undefined") return;
    const now = Date.now();
    const lastSave = lastSaveMap.get(id) || 0;
    
    // Save to localStorage every 1 second
    if (now - lastSave > 1000) {
        try {
            localStorage.setItem(`task_prog_${id}`, JSON.stringify({
                displayProgress,
                updatedAt: now
            }));
            lastSaveMap.set(id, now);
        } catch (e) {}
    }
}

function getSavedProgress(id: string, backendProgress: number, expectedDurationMs: number, status: string): number {
    if (typeof window === "undefined") return backendProgress;
    
    if (status === "completed") return 100;
    if (status === "failed" || status === "error" || status === "not_found") return backendProgress;

    try {
        const savedStr = localStorage.getItem(`task_prog_${id}`);
        if (!savedStr) return backendProgress;
        
        const saved = JSON.parse(savedStr);
        if (!saved || typeof saved.displayProgress !== "number" || typeof saved.updatedAt !== "number") {
             return backendProgress;
        }

        const elapsedMs = Date.now() - saved.updatedAt;
        // If data is older than 5 times the expected duration, might be stale.
        const maxStaleTime = (expectedDurationMs || 60000) * 5;
        if (elapsedMs < 0 || elapsedMs > maxStaleTime) {
            return Math.max(saved.displayProgress, backendProgress);
        }

        const cap = (status === "analyzing" || status === "active") ? 98 : 90;
        let newDisplay = saved.displayProgress;
        const avgTimeMs = expectedDurationMs || 60000;
        
        if (newDisplay < cap) {
             // Approximate how much progress we should have made while offline
             const baseSpeedPerMs = 100 / avgTimeMs;
             newDisplay += baseSpeedPerMs * elapsedMs;
             if (newDisplay > cap) newDisplay = cap;
        }
        
        return Math.max(newDisplay, backendProgress);
    } catch (e) {
        return backendProgress;
    }
}

function startTicker() {
    if (ticker) return;
    ticker = setInterval(() => {
        let activeCount = 0;
        
        tasksMap.forEach((task, id) => {
            if (task.subscribers.size === 0) return;
            activeCount++;
            
            const avgTimeMs = task.expectedDurationMs || 60000;
            const baseSpeed = (100 / avgTimeMs) * 50;

            if (task.status === "completed" || task.status === "failed" || task.status === "error" || task.status === "not_found") {
                 let finalVal = 100;
                 if (task.status === "failed" || task.status === "error" || task.status === "not_found") {
                     finalVal = task.backendProgress;
                 }
                 if (task.displayProgress !== finalVal) {
                     task.displayProgress = finalVal;
                     task.subscribers.forEach(cb => cb(finalVal));
                 }
                 return;
            }

            let prev = task.displayProgress;
            let next = prev;

            if (prev >= task.backendProgress) {
                const cap = (task.status === "analyzing" || task.status === "active") ? 98 : 90;
                if (prev < cap && (task.status === "scraping" || task.status === "analyzing" || task.status === "active" || task.status === "pending" || task.status === "starting")) {
                    const distance = cap - prev;
                    // Slow down gracefully as we approach the cap
                    const slowDownFactor = Math.max(0.1, Math.min(1, distance / 20)); 
                    const speed = Math.max(0.005, baseSpeed * slowDownFactor); 
                    next = Math.min(prev + speed, cap);
                }
            } else {
                // Catching up to backend progress (backend jumped ahead)
                const diff = task.backendProgress - prev;
                const step = Math.max(diff * 0.08, 0.4);
                next = Math.min(prev + step, task.backendProgress);
            }

            if (task.backendProgress < prev && task.backendProgress < 5) {
                if (id === "default_id" || task.status === "starting" || task.status === "idle") {
                    next = task.backendProgress;
                }
            }

            if (next !== prev) {
                task.displayProgress = next;
                task.subscribers.forEach(cb => cb(next));
                saveTaskProgress(id, next);
            }
        });

        if (activeCount === 0) {
            clearInterval(ticker!);
            ticker = null;
        }
    }, 50);
}

export function useSmoothProgress(
    taskId: string | null | undefined, 
    backendProgress: number, 
    status: string,
    expectedDurationMs: number = 60000
): { displayProgress: number } {
  const [displayProgress, setDisplayProgress] = useState(() => {
      const id = taskId || "default_id";
      if (tasksMap.has(id)) {
          return Math.max(tasksMap.get(id)!.displayProgress, backendProgress);
      }
      return getSavedProgress(id, backendProgress, expectedDurationMs, status);
  });

  useEffect(() => {
      const id = taskId || "default_id";

      if (!tasksMap.has(id)) {
          const initialProgress = getSavedProgress(id, backendProgress, expectedDurationMs, status);
          tasksMap.set(id, {
              backendProgress,
              status,
              displayProgress: initialProgress,
              expectedDurationMs,
              subscribers: new Set()
          });
      }

      const taskObj = tasksMap.get(id)!;
      taskObj.backendProgress = backendProgress;
      taskObj.status = status;
      if (expectedDurationMs && expectedDurationMs > 0) {
          taskObj.expectedDurationMs = expectedDurationMs;
      }

      const cb = (val: number) => {
          setDisplayProgress(val);
      };
      
      taskObj.subscribers.add(cb);
      startTicker();

      return () => {
          taskObj.subscribers.delete(cb);
      };
  }, [taskId, backendProgress, status, expectedDurationMs]);

  return { displayProgress };
}

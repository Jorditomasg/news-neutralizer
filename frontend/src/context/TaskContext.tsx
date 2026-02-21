"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";

export interface TaskItem {
  id: string;
  title: string;
  status: "pending" | "active" | "completed" | "error";
  progress: number;
  message: string;
  timestamp: number;
}

interface TaskContextType {
  tasks: TaskItem[];
  addTask: (id: string, title: string) => void;
  updateTaskProgress: (id: string, progress: number, message: string) => void;
  completeTask: (id: string, message: string) => void;
  failTask: (id: string, message: string) => void;
  removeTask: (id: string) => void;
  clearCompletedTasks: () => void;
}

const STORAGE_KEY = "nn_tasks";

function loadTasks(): TaskItem[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as TaskItem[];
  } catch {
    return [];
  }
}

function saveTasks(tasks: TaskItem[]) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
  } catch {
    // quota exceeded — ignore
  }
}

const TaskContext = createContext<TaskContextType | undefined>(undefined);

export function TaskProvider({ children }: { children: ReactNode }) {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [hydrated, setHydrated] = useState(false);

  // Hydrate from localStorage on mount (client only)
  useEffect(() => {
    setTasks(loadTasks());
    setHydrated(true);
  }, []);

  // Persist every time tasks change (after hydration)
  useEffect(() => {
    if (hydrated) saveTasks(tasks);
  }, [tasks, hydrated]);

  const addTask = useCallback((id: string, title: string) => {
    setTasks((prev) => {
      if (prev.find((t) => t.id === id)) return prev;
      return [...prev, { id, title, status: "pending", progress: 0, message: "Iniciando...", timestamp: Date.now() }];
    });
  }, []);

  const updateTaskProgress = useCallback((id: string, progress: number, message: string) => {
    setTasks((prev) =>
      prev.map((t) => (t.id === id ? { ...t, status: "active", progress, message } : t))
    );
  }, []);

  const completeTask = useCallback((id: string, message: string) => {
    setTasks((prev) =>
      prev.map((t) => (t.id === id ? { ...t, status: "completed", progress: 100, message } : t))
    );
  }, []);

  const failTask = useCallback((id: string, message: string) => {
    setTasks((prev) =>
      prev.map((t) => (t.id === id ? { ...t, status: "error", message } : t))
    );
  }, []);

  const removeTask = useCallback((id: string) => {
    setTasks((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const clearCompletedTasks = useCallback(() => {
    setTasks((prev) => prev.filter((t) => t.status !== "completed" && t.status !== "error"));
  }, []);

  return (
    <TaskContext.Provider value={{ tasks, addTask, updateTaskProgress, completeTask, failTask, removeTask, clearCompletedTasks }}>
      {children}
    </TaskContext.Provider>
  );
}

export function useTaskContext() {
  const context = useContext(TaskContext);
  if (context === undefined) {
    throw new Error("useTaskContext must be used within a TaskProvider");
  }
  return context;
}

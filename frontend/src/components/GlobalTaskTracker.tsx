"use client";

import { useEffect } from "react";
import { useTaskContext, TaskItem } from "@/context/TaskContext";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

// Child component to handle individual task WebSocket connection
function TaskConnection({ task }: { task: TaskItem }) {
  const { updateTaskProgress, completeTask, failTask } = useTaskContext();

  useEffect(() => {
    if (task.status === "completed" || task.status === "error") return;

    const ws = new WebSocket(`${WS_BASE}/api/v1/ws/tasks/${task.id}`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.status === "completed") {
        completeTask(task.id, "Hechos extraídos, listos para generar noticia neutral.");
        ws.close();
      } else if (data.status === "failed") {
        failTask(task.id, data.error_message || "Ocurrió un error al procesar la noticia.");
        ws.close();
      } else {
        const progress = data.progress || 0;
        const msg = data.progress_message || `Procesando... ${progress}%`;
        updateTaskProgress(task.id, progress, msg);
      }
    };

    ws.onerror = () => {
      // Ignoring minor connection drop errors intentionally
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    };
  }, [task.id, task.status, completeTask, failTask, updateTaskProgress]);

  return null;
}

export function GlobalTaskTracker() {
  const { tasks } = useTaskContext();

  return (
    <>
      {/* Invisible workers to manage WebSocket connections for active tasks */}
      {tasks
        .filter(t => t.status === "pending" || t.status === "active")
        .map(task => (
          <TaskConnection key={task.id} task={task} />
        ))}
    </>
  );
}

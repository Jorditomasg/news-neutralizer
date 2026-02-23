"use client";

import { useState, useRef, useEffect } from "react";
import { useTaskContext } from "@/context/TaskContext";
import Link from "next/link";
import { useRouter } from "next/navigation";

export function NotificationCenter() {
  const { tasks, clearCompletedTasks } = useTaskContext();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  const activeTasksCount = tasks.filter(t => t.status === "active" || t.status === "pending").length;
  const hasUnread = tasks.length > 0; // Simple unread logic for now

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed": return "bg-teal-500 text-teal-950";
      case "error": return "bg-red-500 text-red-950";
      case "active": return "bg-cyan-500 text-cyan-950";
      default: return "bg-gray-500 text-gray-950";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed": return "✓";
      case "error": return "✕";
      case "active": return "↻";
      default: return "⋯";
    }
  };

  return (
    <div className="relative" ref={menuRef}>
      {/* Notification Bell Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors rounded-lg hover:bg-gray-100 dark:hover:bg-white/5"
        aria-label="Notificaciones"
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
        
        {/* Active badge */}
        {activeTasksCount > 0 ? (
          <span className="absolute top-1 right-1 flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-teal-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-teal-500 border-2 border-gray-950"></span>
          </span>
        ) : hasUnread ? (
          <span className="absolute top-1.5 right-1.5 block h-2 w-2 rounded-full bg-cyan-500 border border-gray-950"></span>
        ) : null}
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white dark:bg-gray-900 border border-gray-200 dark:border-white/10 rounded-2xl shadow-xl dark:shadow-2xl overflow-hidden z-50 animate-fade-in origin-top-right transition-colors">
          <div className="px-4 py-3 border-b border-gray-100 dark:border-white/5 flex justify-between items-center bg-gray-50 dark:bg-gray-950/50 transition-colors">
            <h3 className="font-semibold text-gray-900 dark:text-white">Tareas en Segundo Plano</h3>
            <span className="text-xs font-medium bg-gray-200 dark:bg-white/10 text-gray-700 dark:text-gray-300 px-2 py-1 rounded-md transition-colors">
              {activeTasksCount} activas
            </span>
          </div>
          
          <div className="max-h-[60vh] overflow-y-auto overscroll-contain bg-white dark:bg-gray-900 transition-colors">
            {tasks.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
                No hay tareas recientes.
              </div>
            ) : (
              <ul className="divide-y divide-gray-100 dark:divide-white/5">
                {[...tasks].sort((a, b) => b.timestamp - a.timestamp).map((task) => (
                  <li key={task.id} className="p-4 hover:bg-gray-50 dark:hover:bg-white/[0.02] transition-colors group">
                    <div className="flex gap-3">
                      <div className={`mt-0.5 shrink-0 flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${getStatusColor(task.status)} ${task.status === 'active' ? 'animate-pulse' : ''}`}>
                         {getStatusIcon(task.status)}
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex justify-between items-start mb-1">
                          <p className="text-sm font-medium text-gray-900 dark:text-white truncate pr-2 transition-colors" title={task.title}>
                            {task.title || "Procesando URL..."}
                          </p>
                          <span className="text-xs text-gray-500 dark:text-gray-400 font-mono shrink-0 transition-colors">
                            {task.progress}%
                          </span>
                        </div>
                        
                        <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-1 mb-2 transition-colors">
                          {task.message}
                        </p>
                        
                        {/* Miniature Progress Bar */}
                        <div className="w-full h-1.5 bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden mb-2 transition-colors">
                          <div 
                            className={`h-full rounded-full transition-all duration-500 ${
                              task.status === "error" ? "bg-red-500" :
                              task.status === "completed" ? "bg-teal-500" :
                              "bg-gradient-to-r from-cyan-500 to-teal-400 dark:from-cyan-400 dark:to-teal-400"
                            }`}
                            style={{ width: `${task.progress}%` }}
                          />
                        </div>

                        {/* Actions */}
                        <div className="flex justify-end mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={() => {
                              setIsOpen(false);
                              router.push(`/search?taskId=${task.id}`);
                            }}
                            className="text-xs font-semibold text-teal-600 dark:text-teal-400 hover:text-teal-500 dark:hover:text-teal-300 transition-colors"
                          >
                            Ver Detalles &rarr;
                          </button>
                        </div>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
          
          {tasks.filter(t => t.status === "completed" || t.status === "error").length > 0 && (
            <div className="p-2 border-t border-gray-100 dark:border-white/5 bg-gray-50 dark:bg-gray-950/30 transition-colors">
              <button 
                onClick={clearCompletedTasks}
                className="w-full py-2 text-xs font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors rounded-lg hover:bg-gray-200 dark:hover:bg-white/5"
              >
                Limpiar completadas
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

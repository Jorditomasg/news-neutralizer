"use client";

import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
import { sessionHeaders } from "@/lib/session";
import { useI18n } from "@/context/I18nContext";

interface FeedbackButtonsProps {
  targetType: "analysis" | "article" | "domain";
  targetId: string | number;
  className?: string;
  compact?: boolean;
}

export function FeedbackButtons({ targetType, targetId, className = "", compact = false }: Readonly<FeedbackButtonsProps>) {
  const { t } = useI18n();
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [selectedVote, setSelectedVote] = useState<string | null>(null);

  const handleVote = async (vote: "like" | "dislike" | "neutral") => {
    if (status === "loading" || selectedVote === vote) return;
    
    try {
      setStatus("loading");
      setSelectedVote(vote);
      
      const res = await fetch(`${API_BASE}/api/v1/feedback/`, {
        method: "POST",
        headers: sessionHeaders(),
        body: JSON.stringify({
          target_type: targetType,
          target_id: String(targetId),
          vote: vote
        })
      });

      if (!res.ok) throw new Error("Error recording feedback");
      setStatus("success");
      
      // Auto reset success status after a delay
      setTimeout(() => setStatus("idle"), 2000);
      
    } catch (e) {
      console.error(e);
      setStatus("error");
      setSelectedVote(null); // Reset visual selection on error
    }
  };

  if (compact) {
    return (
      <div className={`flex items-center gap-1 ${className}`}>
        <button 
          onClick={(e) => { e.preventDefault(); handleVote("like"); }}
          className={`p-1.5 rounded-md transition-colors ${selectedVote === "like" ? "bg-teal-100 dark:bg-teal-500/20 text-teal-700 dark:text-teal-400" : "text-gray-400 dark:text-gray-500 hover:text-teal-600 dark:hover:text-teal-400 hover:bg-gray-100 dark:hover:bg-white/5"}`}
          title={t.feedback.good}
        >
          <svg className="w-3.5 h-3.5" fill={selectedVote === "like" ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" /></svg>
        </button>
        <button 
          onClick={(e) => { e.preventDefault(); handleVote("dislike"); }}
          className={`p-1.5 rounded-md transition-colors ${selectedVote === "dislike" ? "bg-red-100 dark:bg-red-500/20 text-red-600 dark:text-red-400" : "text-gray-400 dark:text-gray-500 hover:text-red-600 dark:hover:text-red-400 hover:bg-gray-100 dark:hover:bg-white/5"}`}
          title={t.feedback.bad}
        >
          <svg className="w-3.5 h-3.5" fill={selectedVote === "dislike" ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" /></svg>
        </button>
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <span className="text-xs text-gray-500 dark:text-gray-400 mr-2 transition-colors">{t.feedback.question}</span>
      <button 
        onClick={() => handleVote("like")}
        disabled={status === "loading"}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
          selectedVote === "like" 
            ? "bg-teal-100 dark:bg-teal-500/20 text-teal-700 dark:text-teal-400 border py-[0.3125rem] px-[0.6875rem] border-teal-200 dark:border-teal-500/30" 
            : "bg-gray-100 dark:bg-white/5 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-200 dark:hover:bg-white/10"
        }`}
      >
        <svg className="w-4 h-4" fill={selectedVote === "like" ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" /></svg>
        {t.feedback.useful}
      </button>

      <button 
        onClick={() => handleVote("neutral")}
        disabled={status === "loading"}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
          selectedVote === "neutral" 
            ? "bg-gray-200 dark:bg-gray-500/20 text-gray-700 dark:text-gray-300 border py-[0.3125rem] px-[0.6875rem] border-gray-300 dark:border-gray-500/30" 
            : "bg-gray-100 dark:bg-white/5 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-200 dark:hover:bg-white/10"
        }`}
      >
        <svg className="w-4 h-4" fill={selectedVote === "neutral" ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14" /></svg>
        Regular
      </button>

      <button 
        onClick={() => handleVote("dislike")}
        disabled={status === "loading"}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
          selectedVote === "dislike" 
            ? "bg-red-100 dark:bg-red-500/20 text-red-600 dark:text-red-400 border py-[0.3125rem] px-[0.6875rem] border-red-200 dark:border-red-500/30" 
            : "bg-gray-100 dark:bg-white/5 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-200 dark:hover:bg-white/10"
        }`}
      >
        <svg className="w-4 h-4" fill={selectedVote === "dislike" ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" /></svg>
        {t.feedback.not_useful}
      </button>
      
      {status === "success" && (
        <span className="text-xs text-teal-600 dark:text-teal-400 ml-2 animate-fade-in transition-colors">¡Gracias!</span>
      )}
    </div>
  );
}

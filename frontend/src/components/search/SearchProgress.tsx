import React, { useMemo } from "react";

interface SearchProgressProps {
  status: string;
  progress: number; // 0-100 (global progress)
  message: string;
}

type StepStatus = "pending" | "active" | "completed";

interface Step {
  id: string;
  label: string;
  status: StepStatus;
  localProgress: number; // 0-100 (progress within this step)
}

export function SearchProgress({ status, progress, message }: SearchProgressProps) {
  
  const steps = useMemo<Step[]>(() => {
    // 1. Search Step (0-15%)
    let searchStatus: StepStatus = "pending";
    let searchProgress = 0;

    if (progress >= 15 || status === "scraping" || status === "analyzing" || status === "completed") {
      searchStatus = "completed";
      searchProgress = 100;
    } else {
      searchStatus = "active"; // Starts active
      // Normalize 0-15 to 0-100
      searchProgress = Math.min(100, (progress / 15) * 100);
    }

    // 2. Extraction Step (15-60%)
    let extractStatus: StepStatus = "pending";
    let extractProgress = 0;

    if (progress >= 60 || status === "analyzing" || status === "completed") {
      extractStatus = "completed";
      extractProgress = 100;
    } else if (progress >= 15 || status === "scraping") {
      extractStatus = "active";
      // Normalize 15-60 to 0-100
      extractProgress = Math.min(100, Math.max(0, (progress - 15) / (60 - 15) * 100));
    }

    // 3. Analysis Step (60-100%)
    let analysisStatus: StepStatus = "pending";
    let analysisProgress = 0;

    if (status === "completed") {
        analysisStatus = "completed";
        analysisProgress = 100;
    } else if (progress >= 60 || status === "analyzing") {
      analysisStatus = "active";
      // Normalize 60-100 to 0-100
      analysisProgress = Math.min(100, Math.max(0, (progress - 60) / (100 - 60) * 100));
    }
    
    // Override for specific statuses
    if (status === "starting" || status === "pending" || status === "headlines_loading" || status === "headlines_selection") {
         searchStatus = "active";
         extractStatus = "pending";
         analysisStatus = "pending";
         if (status === "pending") searchProgress = 50; // Fake progress for queue
    }

    return [
      { id: "search", label: "Búsqueda", status: searchStatus, localProgress: searchProgress },
      { id: "extract", label: "Extracción", status: extractStatus, localProgress: extractProgress },
      { id: "analyze", label: "Análisis", status: analysisStatus, localProgress: analysisProgress },
    ];
  }, [status, progress]);

  const activeStep = steps.find(s => s.status === "active") || steps[steps.length - 1];
  const activeProgress = activeStep.localProgress;

  return (
    <div className="w-full max-w-4xl mx-auto my-12 animate-fade-in relative z-20">
      <div className="relative overflow-hidden bg-white/70 dark:bg-gray-950/40 backdrop-blur-xl border border-gray-200 dark:border-white/10 rounded-3xl p-8 md:p-12 shadow-xl dark:shadow-[0_0_100px_rgba(45,212,191,0.1)] ring-1 ring-gray-100 dark:ring-white/5 transition-colors">
        
        {/* Decorative background glow */}
        <div className="absolute -top-24 -right-24 w-64 h-64 bg-teal-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-64 h-64 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

        {/* Header Section */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 mb-12 relative z-10">
          <div>
             <h2 className="text-2xl md:text-3xl font-display font-bold text-gray-900 dark:text-white mb-2 tracking-tight transition-colors">
               Analizando <span className="text-teal-600 dark:text-teal-400 opacity-90 transition-colors">"{activeStep.label}"</span>
             </h2>
             <p className="text-gray-600 dark:text-gray-400 max-w-lg text-sm md:text-base leading-relaxed transition-colors">
               {message || (status === "scraping" ? "Extrayendo información clave de múltiples fuentes..." : 
                status === "analyzing" ? "Detectando sesgos y verificando hechos con IA..." : 
                "Iniciando el motor de búsqueda neutral...")}
             </p>
          </div>
          
          {/* Circular Progress Indicator */}
          <div className="relative w-16 h-16 md:w-20 md:h-20 flex items-center justify-center shrink-0">
             <svg className="w-full h-full rotate-[-90deg]" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="45" fill="none" className="stroke-gray-200 dark:stroke-white/10" strokeWidth="6" />
                <circle 
                  cx="50" cy="50" r="45" fill="none" stroke="url(#gradient)" strokeWidth="6" 
                  strokeDasharray="283" 
                  strokeDashoffset={283 - (283 * activeProgress) / 100}
                  className="transition-all duration-500 ease-out"
                />
                <defs>
                  <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#2dd4bf" />
                    <stop offset="100%" stopColor="#22d3ee" />
                  </linearGradient>
                </defs>
             </svg>
             <span className="absolute text-sm md:text-base font-mono font-bold text-teal-600 dark:text-teal-400 transition-colors">{Math.round(activeProgress)}%</span>
          </div>
        </div>

        {/* Steps Visualization */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 relative z-10">
          {steps.map((step, index) => {
            const isActive = step.status === "active";
            const isCompleted = step.status === "completed";
            
            return (
              <div 
                key={step.id} 
                className={`relative overflow-hidden rounded-2xl p-6 transition-all duration-500 border ${
                  isActive 
                    ? "bg-white dark:bg-white/[0.03] border-teal-500/30 ring-1 ring-teal-500/20 shadow-lg shadow-teal-500/5 dark:shadow-teal-900/10" 
                    : isCompleted
                      ? "bg-teal-50 dark:bg-teal-500/[0.02] border-teal-200 dark:border-teal-500/10 opacity-70"
                      : "bg-gray-100/50 dark:bg-gray-900/20 border-gray-200 dark:border-white/5 opacity-60 dark:opacity-40 grayscale"
                }`}
              >
                {isActive && <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-teal-500 via-cyan-400 to-teal-500 animate-loading-bar" />}
                
                <div className="flex items-center justify-between mb-3">
                   <div className={`p-2 rounded-lg ${isActive ? "bg-teal-100 dark:bg-teal-500/10 text-teal-600 dark:text-teal-400" : isCompleted ? "bg-teal-100 dark:bg-teal-500/10 text-teal-600 dark:text-teal-500" : "bg-gray-200 dark:bg-white/5 text-gray-500"}`}>
                      {isCompleted ? (
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" /></svg>
                      ) : (
                        <span className="font-bold font-mono text-sm">{index + 1}</span>
                      )}
                   </div>
                   {isActive && <div className="w-2 h-2 rounded-full bg-teal-500 dark:bg-teal-400 animate-pulse shadow-[0_0_10px_#2dd4bf]" />}
                </div>
                
                <h3 className={`font-bold text-lg mb-1 transition-colors ${isActive ? "text-gray-900 dark:text-white" : isCompleted ? "text-gray-700 dark:text-gray-300" : "text-gray-500"}`}>
                  {step.label}
                </h3>
              </div>
            );
          })}
        </div>

      </div>
    </div>
  );
}

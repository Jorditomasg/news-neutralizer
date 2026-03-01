import React, { useMemo } from "react";
import { useI18n } from "@/context/I18nContext";

interface SearchProgressProps {
  status: string;
  progress: number;
  message: string;
  expectedDurationMs?: number;
}

type StepStatus = "pending" | "active" | "completed";

interface Step {
  id: string;
  label: string;
  status: StepStatus;
}

export function SearchProgress({ status, progress, message, expectedDurationMs }: SearchProgressProps) {
  const { t } = useI18n();
  const formatTime = (ms: number) => {
      const totalSeconds = Math.floor(ms / 1000);
      const minutes = Math.floor(totalSeconds / 60);
      const seconds = totalSeconds % 60;
      return `${minutes}:${seconds.toString().padStart(2, '0')} min`;
  };
  
  const steps = useMemo<Step[]>(() => {
    // 1. Search & Extract
    let step1: StepStatus = "pending";
    if (progress >= 33 || status === "analyzing" || status === "completed") step1 = "completed";
    else if (status === "scraping" || status === "active" || status === "pending" || progress > 0) step1 = "active";

    // 2. AI Analysis
    let step2: StepStatus = "pending";
    if (progress >= 80 || status === "completed") step2 = "completed";
    else if (progress >= 33 || status === "analyzing") step2 = "active";

    // 3. Generation & Consolidation
    let step3: StepStatus = "pending";
    if (status === "completed" || progress >= 95) step3 = "completed";
    else if (progress >= 80) step3 = "active";
    
    // Fallbacks
    if (status === "starting") {
        step1 = "active"; step2 = "pending"; step3 = "pending";
    }

    return [
      { id: "extract", label: t?.search.progress_step1, status: step1 },
      { id: "analyze", label: t?.search.progress_step2, status: step2 },
      { id: "generate", label: t?.search.progress_step3, status: step3 },
    ];
  }, [status, progress, t]);

  return (
    <div className="w-full max-w-4xl mx-auto my-6 animate-fade-in relative z-20">
      <div className="relative overflow-hidden py-4 transition-colors">
        
        <div className="text-center mb-12 relative z-10">
             <p className="text-gray-600 dark:text-gray-400 max-w-lg mx-auto text-sm md:text-base leading-relaxed transition-colors mb-2">
               {message || t?.search.progress_message_start}
             </p>
        </div>

        <div className="relative z-10 w-full max-w-3xl mx-auto mb-12">
           <div className="flex items-start justify-between relative">
             
             {/* Background connecting line */}
             <div className="absolute top-5 left-[16%] right-[16%] h-0.5 bg-gray-200 dark:bg-gray-800 -z-20" />
             
             {steps.map((step, index) => {
               const isActive = step.status === "active";
               const isCompleted = step.status === "completed";
               
               return (
                 <div key={step.id} className="flex flex-col items-center w-1/3 text-center relative pointer-events-none">
                    {/* Connecting line progress (foreground) */}
                    <div className="absolute top-5 right-[50%] left-[-50%] h-0.5 -z-10 origin-left overflow-hidden">
                       {index > 0 && (
                         <div 
                           className={`h-full bg-teal-500 transition-all duration-1000 ease-in-out ${
                              isCompleted || isActive ? 'w-full' : 'w-0'
                           }`} 
                         />
                       )}
                    </div>
                 
                    {/* Circle Node */}
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center border-2 mb-4 transition-all duration-500 bg-white dark:bg-gray-900 relative ${
                        isCompleted 
                          ? "border-teal-500 bg-teal-50 dark:bg-teal-500/10 text-teal-600 dark:text-teal-400 shadow-[0_0_15px_rgba(20,184,166,0.1)]" 
                          : isActive 
                            ? "border-teal-400 ring-4 ring-teal-500/20 shadow-[0_0_20px_rgba(45,212,191,0.3)] text-teal-500" 
                            : "border-gray-200 dark:border-gray-800 text-gray-400 dark:text-gray-600"
                    }`}>
                      {isCompleted ? (
                         <svg className="w-5 h-5 animate-[scale-in_0.3s_ease-out]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                           <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                         </svg>
                      ) : isActive ? (
                         <div className="w-3 h-3 rounded-full bg-teal-500 animate-[ping_1.5s_cubic-bezier(0,0,0.2,1)_infinite] opacity-80" />
                      ) : (
                         <span className="text-sm font-bold">{index + 1}</span>
                      )}
                      
                      {/* Active breathing outer glow */}
                      {isActive && (
                         <div className="absolute inset-0 rounded-full border-2 border-teal-400 opacity-20 animate-[ping_2s_cubic-bezier(0,0,0.2,1)_infinite]" />
                      )}
                    </div>
                    
                    {/* Step Label */}
                    <div className={`text-xs md:text-sm font-semibold transition-all duration-500 ${
                      isActive ? "text-gray-900 dark:text-teal-300 transform scale-105" :
                      isCompleted ? "text-gray-600 dark:text-teal-200/60" :
                      "text-gray-400 dark:text-gray-600"
                    }`}>
                        {step.label}
                    </div>
                 </div>
               )
             })}
           </div>
        </div>

        {/* Minimalist Horizontal Progress Bar */}
        <div className="relative z-10 w-full max-w-2xl mx-auto mt-6">
           <div className="flex justify-between items-end mb-2 px-1">
              <div className="flex-1"></div>
              
              <div className="flex-1 text-center">
                  <span className="text-3xl md:text-4xl font-display font-bold bg-clip-text text-transparent bg-gradient-to-r from-teal-600 to-cyan-500 dark:from-teal-400 dark:to-cyan-400 transition-all font-mono tracking-tight">
                     {Math.round(progress)}%
                  </span>
              </div>
              
              <div className="flex-1 flex justify-end pb-1 md:pb-1.5">
                 {expectedDurationMs && expectedDurationMs > 0 && status !== 'completed' && (
                     <span className="text-xs font-mono font-medium text-gray-400 dark:text-gray-500 flex items-center gap-1.5 opacity-80">
                         <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                             <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                         </svg>
                         ~{formatTime(expectedDurationMs)}
                     </span>
                 )}
              </div>
           </div>
           
           <div className="h-2 sm:h-2.5 w-full bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden shadow-inner">
              <div 
                className="h-full bg-gradient-to-r from-teal-500 via-cyan-400 to-teal-400 transition-all ease-out duration-300 relative"
                style={{ width: `${Math.max(2, progress)}%` }} // Minimum 2% width
              >
                  <div className="absolute top-0 left-0 w-full h-full bg-white/20 animate-[shimmer_2s_infinite]" />
              </div>
           </div>
        </div>

      </div>
    </div>
  );
}

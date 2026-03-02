"use client";

interface PageHeaderProps {
  readonly title: string;
  readonly gradient?: "teal" | "purple";
}

const gradients = {
  teal: "bg-gradient-to-b from-teal-500 to-cyan-500 dark:from-teal-400 dark:to-cyan-500",
  purple: "bg-gradient-to-b from-purple-500 to-pink-500 dark:from-purple-400 dark:to-pink-500",
};

export function PageHeader({ title, gradient = "teal" }: PageHeaderProps) {
  return (
    <div className="flex items-center gap-3 mb-8">
      <div className={`h-8 w-1 rounded-full ${gradients[gradient]}`} />
      <h1 className="font-display text-3xl font-bold text-gray-900 dark:text-white transition-colors">
        {title}
      </h1>
    </div>
  );
}

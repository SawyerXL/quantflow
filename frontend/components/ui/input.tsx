import { cn } from "@/lib/utils";
import { InputHTMLAttributes, forwardRef } from "react";

export const Input = forwardRef<
  HTMLInputElement,
  InputHTMLAttributes<HTMLInputElement>
>(({ className, ...props }, ref) => (
  <input
    ref={ref}
    className={cn(
      "w-full px-3 py-2 rounded-lg border border-surface-300 bg-white text-surface-900 placeholder-surface-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-shadow text-sm",
      className,
    )}
    {...props}
  />
));

Input.displayName = "Input";

"use client";

import Link from "next/link";
import { useAuth } from "@/hooks/use-auth";

export function StartForFreeLink({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const { isLoggedIn } = useAuth();
  const href = isLoggedIn ? "/backtest" : "/register";
  return (
    <Link href={href} className={className}>
      {children}
    </Link>
  );
}

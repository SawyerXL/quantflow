"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Animate a number from 0 to `end` over `duration` ms.
 * Only triggers when `start` is true and the element is visible.
 */
export function useCountUp(
  end: number,
  duration: number = 1200,
  start: boolean = true,
) {
  const [value, setValue] = useState(0);
  const frameRef = useRef<number>(0);
  const startTimeRef = useRef<number>(0);

  useEffect(() => {
    if (!start) return;
    startTimeRef.current = 0;

    const animate = (timestamp: number) => {
      if (!startTimeRef.current) startTimeRef.current = timestamp;
      const elapsed = timestamp - startTimeRef.current;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(eased * end);

      if (progress < 1) {
        frameRef.current = requestAnimationFrame(animate);
      }
    };

    frameRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frameRef.current);
  }, [end, duration, start]);

  return value;
}

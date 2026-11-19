"use client";

import React, { useState } from "react";
import Image from "next/image";
import { cn } from "@/lib/utils";

interface BrandLogoProps {
  size?: number;
  showWordmark?: boolean;
  className?: string;
  priority?: boolean;
}

export function BrandLogo({
  size = 32,
  showWordmark = false,
  className,
  priority = true,
}: BrandLogoProps) {
  const [useFallback, setUseFallback] = useState(false);

  // PlaneByte official logo dimensions
  // Primary: /brand/mark.svg (vector)
  // Fallback: /brand/pb-mark.png or /pb-logo.png
  const src = useFallback ? "/brand/pb-mark.png" : "/brand/mark.svg";

  return (
    <span className={cn("inline-flex items-center gap-2 select-none", className)}>
      <span
        className="relative inline-flex shrink-0 items-center justify-center overflow-hidden"
        style={{ width: size, height: size }}
      >
        <Image
          src={src}
          alt="PlaneByte Logo"
          width={size}
          height={size}
          priority={priority}
          unoptimized
          onError={() => setUseFallback(true)}
          className="h-full w-full object-contain"
        />
      </span>
      {showWordmark && (
        <span className="font-bold tracking-tight text-foreground text-sm sm:text-base leading-none">
          PlaneByte
        </span>
      )}
    </span>
  );
}

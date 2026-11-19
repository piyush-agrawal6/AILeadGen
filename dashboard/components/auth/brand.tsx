"use client";

import React from 'react';
import { BrandLogo } from '@/components/ui/BrandLogo';
import { brand } from '@/lib/brand';

export { BrandLogo };

export function PlaneByteBrand({ compact = false }: { compact?: boolean }) {
  return (
    <span className="heysow-wordmark inline-flex items-center gap-2">
      <BrandLogo size={32} showWordmark={!compact} priority />
    </span>
  );
}

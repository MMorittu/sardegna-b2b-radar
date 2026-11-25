import React from 'react';
import Image from 'next/image';

interface LogoProps {
  className?: string;
  showText?: boolean;
  variant?: 'monochrome' | 'negative';
}

export default function Logo({
  className = 'h-8',
  showText = true,
  variant = 'negative',
}: LogoProps) {
  const logoSrc = variant === 'negative' ? '/brand/logo-negative.svg' : '/brand/logo-monochrome.svg';

  return (
    <div className="flex items-center gap-3 select-none">
      <div className={`aspect-[745/590] relative flex items-center justify-center shrink-0 ${className}`}>
        <Image
          src={logoSrc}
          alt="Sardegna B2B Radar Logo"
          width={100}
          height={100}
          priority
          unoptimized
          className="w-full h-full object-contain"
        />
      </div>

      {showText && (
        <div className="flex flex-col tracking-tight">
          <span className="font-mono text-sm md:text-base font-bold text-white uppercase tracking-wider">
            SARDEGNA
          </span>
          <span className="text-[10px] md:text-xs text-brand-accent font-semibold tracking-widest uppercase">
            B2B Radar
          </span>
        </div>
      )}
    </div>
  );
}

import React from 'react';

export default function Loading() {
  return (
    <main className="min-h-screen bg-brand-surface p-4 md:p-8 space-y-6 animate-pulse">
      {/* Top Bar Skeleton */}
      <div className="h-16 bg-brand-dark/10 border-2 border-brand-dark flex items-center px-4 justify-between" />

      {/* KPI Cards Skeleton */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="h-28 bg-white border-2 border-brand-dark p-4 space-y-3 flex flex-col justify-between"
          >
            <div className="h-4 bg-brand-dark/15 w-2/3" />
            <div className="h-8 bg-brand-dark/25 w-1/2" />
          </div>
        ))}
      </div>

      {/* Filter Bar Skeleton */}
      <div className="h-14 bg-white border-2 border-brand-border" />

      {/* Table / Cards Skeleton */}
      <div className="bg-white border-2 border-brand-dark p-4 space-y-4">
        <div className="h-8 bg-brand-dark/15 w-full" />
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="h-12 bg-brand-surface border border-brand-border w-full" />
        ))}
      </div>
    </main>
  );
}

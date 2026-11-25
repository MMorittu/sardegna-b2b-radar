import React from 'react';
import type { KpiSummary } from '@/lib/types';
import { Target, TrendingUp, Compass, Award } from 'lucide-react';

interface KpiHeaderProps {
  stats: KpiSummary;
}

export default function KpiHeader({ stats }: KpiHeaderProps) {
  const formattedPipeline = new Intl.NumberFormat('it-IT', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0,
  }).format(stats.totalPipelineEur);

  const kpis = [
    {
      label: 'LEAD TOTALI RADAR',
      value: stats.totalLeads.toString(),
      sub: `${stats.byStatus.da_chiamare || 0} da contattare`,
      icon: Target,
      topBorder: 'border-t-2 border-t-brand-dark',
      iconColor: 'text-brand-dark',
      valueColor: 'text-brand-dark',
    },
    {
      label: 'VALORE PIPELINE LAVORI',
      value: formattedPipeline,
      sub: 'Importo complessivo bandi',
      icon: TrendingUp,
      topBorder: 'border-t-2 border-t-brand-accent',
      iconColor: 'text-brand-accent',
      valueColor: 'text-brand-dark',
    },
    {
      label: 'QUALIFICATI ALTA PRIORITÀ',
      value: stats.qualifiedLeads.toString(),
      sub: 'Score rilevanza ≥ 45/100',
      icon: Award,
      topBorder: 'border-t-2 border-t-emerald-600',
      iconColor: 'text-emerald-600',
      valueColor: 'text-emerald-800',
    },
    {
      label: 'VANTAGGIO DIRETTO SILANUS',
      value: stats.advantage40kmLeads.toString(),
      sub: 'Distanza cantiere ≤ 40 km',
      icon: Compass,
      topBorder: 'border-t-2 border-t-brand-accent',
      iconColor: 'text-brand-accent',
      valueColor: 'text-brand-dark',
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4 select-none">
      {kpis.map((kpi, idx) => {
        const Icon = kpi.icon;
        return (
          <div
            key={idx}
            className={`bg-white border border-brand-border/40 p-3.5 md:p-4 flex flex-col justify-between shadow-none transition-colors hover:border-brand-dark ${kpi.topBorder}`}
          >
            <div className="flex items-center justify-between text-brand-muted">
              <span className="text-[10px] md:text-[11px] font-mono font-bold tracking-wider uppercase text-slate-500">
                {kpi.label}
              </span>
              <Icon className={`w-4 h-4 shrink-0 ${kpi.iconColor}`} />
            </div>

            <div className="my-2.5">
              <span className={`font-mono tabular-nums tracking-tight text-xl md:text-2xl lg:text-3xl font-black ${kpi.valueColor}`}>
                {kpi.value}
              </span>
            </div>

            <div className="text-[11px] text-slate-500 font-medium truncate">
              {kpi.sub}
            </div>
          </div>
        );
      })}
    </div>
  );
}

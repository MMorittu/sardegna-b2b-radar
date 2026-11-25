import React from 'react';
import { adminClient } from '@/lib/supabase/admin';
import type { TenderRow, KpiSummary, CrmStatus } from '@/lib/types';
import { DEMO_TENDERS } from '@/lib/demo-data';
import Logo from '@/components/brand/Logo';
import KpiHeader from '@/components/dashboard/KpiHeader';
import LeadsTable from '@/components/dashboard/LeadsTable';

export const revalidate = 0; // Dynamic SSR to ensure fresh CRM and pipeline state

function computeStats(tenders: TenderRow[]): KpiSummary {
  let totalPipelineEur = 0;
  let qualifiedLeads = 0;
  let advantage40kmLeads = 0;
  const byStatus: Record<CrmStatus, number> = {
    da_chiamare: 0,
    preventivo_inviato: 0,
    vinto: 0,
    scartato: 0,
  };

  for (const t of tenders) {
    if (t.amount_eur) {
      totalPipelineEur += t.amount_eur;
    }
    if (t.score >= 45) {
      qualifiedLeads += 1;
    }
    if (t.site_distance_km !== null && t.site_distance_km <= 40) {
      advantage40kmLeads += 1;
    }
    const st = t.crm_status || 'da_chiamare';
    byStatus[st] = (byStatus[st] || 0) + 1;
  }

  return {
    totalLeads: tenders.length,
    totalPipelineEur,
    qualifiedLeads,
    advantage40kmLeads,
    byStatus,
  };
}

async function fetchRadarTenders(): Promise<{
  tenders: TenderRow[];
  stats: KpiSummary;
  isDemoMode: boolean;
}> {
  if (!adminClient) {
    return {
      tenders: DEMO_TENDERS,
      stats: computeStats(DEMO_TENDERS),
      isDemoMode: true,
    };
  }

  try {
    const { data, error } = await adminClient
      .from('tenders')
      .select('*')
      .order('score', { ascending: false })
      .limit(500);

    if (error || !data || data.length === 0) {
      if (error) {
        console.warn('Supabase query error, falling back to portfolio demo data:', error.message);
      }
      return {
        tenders: DEMO_TENDERS,
        stats: computeStats(DEMO_TENDERS),
        isDemoMode: true,
      };
    }

    const tenders = (data as TenderRow[]) || [];
    return {
      tenders,
      stats: computeStats(tenders),
      isDemoMode: false,
    };
  } catch (err) {
    console.warn('Unexpected error connecting to DB, serving portfolio demo data:', err);
    return {
      tenders: DEMO_TENDERS,
      stats: computeStats(DEMO_TENDERS),
      isDemoMode: true,
    };
  }
}

export default async function DashboardPage() {
  const { tenders, stats, isDemoMode } = await fetchRadarTenders();

  return (
    <div className="min-h-screen bg-brand-surface flex flex-col hallmark-stamp">
      {/* Top Industrial Header Bar */}
      <header className="bg-brand-dark text-white border-b-2 border-slate-700/60 px-4 md:px-8 py-3.5 select-none">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-4">
            <Logo className="h-8 md:h-9" showText={true} variant="negative" />
            <div className="hidden sm:block border-l border-brand-border/60 pl-4 text-xs font-mono text-slate-300">
              <span className="block font-bold text-white uppercase text-[11px] tracking-wider">
                Industrial Intelligence Platform
              </span>
              <span>Regional B2B Opportunities & Procurement Radar</span>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs font-mono select-none">
            <div className="flex items-center gap-2 border border-slate-700/60 bg-slate-900/60 px-2.5 py-1.5 rounded-none">
              <span className="relative flex h-2 w-2 shrink-0">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <div className="flex flex-col sm:flex-row sm:items-center sm:gap-2">
                <span className="text-[11px] font-mono text-slate-300 font-semibold tracking-wider uppercase">
                  {isDemoMode ? 'PORTFOLIO DEMO MODE' : 'RADAR ENGINE LIVE'}
                </span>
                <span className="hidden sm:inline text-slate-600 text-[10px]">•</span>
                <span className="text-[10px] text-slate-400 font-mono">
                  {isDemoMode ? 'OFFLINE VERIFIED DATASET' : 'SARDEGNA REGIONAL CORE'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-8 space-y-6">
        {/* KPI Metric Slabs */}
        <KpiHeader stats={stats} />

        {/* Interactive Dual-View Leads Table */}
        <LeadsTable initialTenders={tenders} />
      </main>

      {/* Industrial Footer */}
      <footer className="bg-white border-t-2 border-brand-dark text-brand-muted py-6 px-4 md:px-8 text-xs select-none">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="text-center md:text-left space-y-1">
            <p className="font-bold text-brand-dark font-mono text-[11px] uppercase tracking-wider">
              Sardegna B2B Radar — Open Source Intelligence
            </p>
            <p className="text-[11px]">
              Multi-Source Public Procurement & Regional Grant Radar Engine
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

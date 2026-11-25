'use client';

import React, { useState, useMemo } from 'react';
import type { TenderRow, CrmStatus } from '@/lib/types';
import { updateTenderCrmStatus } from '@/app/actions/crm-actions';
import LeadDrawer from './LeadDrawer';
import {
  Search,
  Filter,
  ArrowUpDown,
  MapPin,
  ChevronRight,
} from 'lucide-react';

interface LeadsTableProps {
  initialTenders: TenderRow[];
}

type DistanceFilter = 'all' | '40' | '100' | 'over100';
type ScoreFilter = 'all' | 'qualified' | 'secondary';
type SortField = 'score' | 'amount' | 'distance' | 'date';

export default function LeadsTable({ initialTenders }: LeadsTableProps) {
  const [tenders, setTenders] = useState<TenderRow[]>(initialTenders);
  const [selectedTender, setSelectedTender] = useState<TenderRow | null>(null);

  // Filters State
  const [searchQuery, setSearchQuery] = useState('');
  const [distanceFilter, setDistanceFilter] = useState<DistanceFilter>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [scoreFilter, setScoreFilter] = useState<ScoreFilter>('all');
  const [cmeOnlyFilter, setCmeOnlyFilter] = useState<boolean>(false);
  const [sortBy, setSortBy] = useState<SortField>('score');
  const [sortAsc, setSortAsc] = useState(false);

  // Status update handler (used by Drawer and Table inline select)
  const handleStatusUpdate = async (
    dedupKey: string,
    newStatus: CrmStatus,
    notes?: string
  ) => {
    // Optimistic UI update
    setTenders((prev) =>
      prev.map((t) =>
        t.dedup_key === dedupKey
          ? {
              ...t,
              crm_status: newStatus,
              crm_notes: notes !== undefined ? notes : t.crm_notes,
            }
          : t
      )
    );

    if (selectedTender?.dedup_key === dedupKey) {
      setSelectedTender((prev) =>
        prev
          ? {
              ...prev,
              crm_status: newStatus,
              crm_notes: notes !== undefined ? notes : prev.crm_notes,
            }
          : null
      );
    }

    try {
      await updateTenderCrmStatus({
        dedupKey,
        status: newStatus,
        notes,
      });
    } catch (err) {
      console.error('Failed to update status on server:', err);
      // Revert if error
      setTenders(initialTenders);
      alert('Errore durante il salvataggio dello stato.');
    }
  };

  // Filtered & Sorted Tenders
  const filteredTenders = useMemo(() => {
    return tenders
      .filter((t) => {
        // Search filter
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const matchCig = t.cig?.toLowerCase().includes(q);
          const matchTitle = t.title.toLowerCase().includes(q);
          const matchEnte = t.contracting_authority.toLowerCase().includes(q);
          const matchComune = t.municipality?.toLowerCase().includes(q);
          const matchCompany = t.winner_company?.toLowerCase().includes(q);
          if (!matchCig && !matchTitle && !matchEnte && !matchComune && !matchCompany) {
            return false;
          }
        }

        // Distance filter
        if (distanceFilter === '40') {
          if (t.site_distance_km === null || t.site_distance_km > 40) return false;
        } else if (distanceFilter === '100') {
          if (t.site_distance_km === null || t.site_distance_km > 100) return false;
        } else if (distanceFilter === 'over100') {
          if (t.site_distance_km !== null && t.site_distance_km <= 100) return false;
        }

        // Status filter
        if (statusFilter !== 'all') {
          if (t.crm_status !== statusFilter) return false;
        }

        // Score filter
        if (scoreFilter === 'qualified') {
          if (t.score < 45) return false;
        } else if (scoreFilter === 'secondary') {
          if (t.score >= 45) return false;
        }

        // CME Analizzato filter
        if (cmeOnlyFilter) {
          if (t.cme_fetch_status !== 'parsed' && t.cme_fetch_status !== 'completed' && t.cme_fetch_status !== 'cme_analyzed') {
            return false;
          }
        }

        return true;
      })
      .sort((a, b) => {
        let diff = 0;
        if (sortBy === 'score') {
          diff = b.score - a.score;
        } else if (sortBy === 'amount') {
          diff = (b.amount_eur || 0) - (a.amount_eur || 0);
        } else if (sortBy === 'distance') {
          diff = (a.site_distance_km ?? 999) - (b.site_distance_km ?? 999);
        } else if (sortBy === 'date') {
          const dateA = a.published_date || a.discovered_at;
          const dateB = b.published_date || b.discovered_at;
          diff = dateB.localeCompare(dateA);
        }
        return sortAsc ? -diff : diff;
      });
  }, [tenders, searchQuery, distanceFilter, statusFilter, scoreFilter, cmeOnlyFilter, sortBy, sortAsc]);

  const getStatusBadge = (status: CrmStatus) => {
    switch (status) {
      case 'vinto':
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 bg-emerald-50 text-emerald-900 font-mono font-bold text-[10px] uppercase border border-emerald-300">
            <span className="w-1.5 h-1.5 bg-emerald-600 rounded-none shrink-0" /> Vinto
          </span>
        );
      case 'preventivo_inviato':
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 bg-sky-50 text-sky-900 font-mono font-bold text-[10px] uppercase border border-sky-300">
            <span className="w-1.5 h-1.5 bg-sky-600 rounded-none shrink-0" /> Offerta Inviata
          </span>
        );
      case 'scartato':
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 bg-slate-100 text-slate-700 font-mono font-bold text-[10px] uppercase border border-slate-300">
            <span className="w-1.5 h-1.5 bg-slate-400 rounded-none shrink-0" /> Scartato
          </span>
        );
      case 'da_chiamare':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 bg-slate-100 text-slate-800 font-mono font-bold text-[10px] uppercase border border-slate-300">
            <span className="w-1.5 h-1.5 bg-brand-dark rounded-none shrink-0" /> Da Contattare
          </span>
        );
    }
  };

  return (
    <div className="space-y-4">
      {/* Control / Filter Bar */}
      <div className="bg-white border-2 border-brand-dark p-3 md:p-4 space-y-3 select-none">
        <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
          {/* Search Box */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-brand-dark absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Cerca per CIG, comune, ente, impresa vincitrice o parole chiave..."
              className="w-full pl-9 pr-3 py-2 text-xs md:text-sm bg-brand-surface border-2 border-brand-dark text-brand-ink placeholder:text-brand-muted focus:outline-none focus:ring-2 focus:ring-brand-accent transition-none"
            />
          </div>

          {/* Quick Counter */}
          <div className="text-right text-xs font-mono font-bold text-brand-dark shrink-0 flex items-center justify-end gap-2">
            <span>RISULTATI:</span>
            <span className="px-2 py-1 bg-brand-dark text-white">
              {filteredTenders.length} / {tenders.length}
            </span>
          </div>
        </div>

        {/* 1-Click Quick Filter Pills & Controls */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-brand-border/30 text-xs select-none">
          {/* Quick Filter Pills */}
          <div className="flex flex-wrap items-center gap-1.5">
            <button
              onClick={() => {
                setDistanceFilter('all');
                setScoreFilter('all');
                setStatusFilter('all');
                setCmeOnlyFilter(false);
              }}
              className={`px-2.5 py-1 text-xs font-bold font-mono transition-none ${
                distanceFilter === 'all' &&
                scoreFilter === 'all' &&
                statusFilter === 'all' &&
                !cmeOnlyFilter
                  ? 'bg-brand-dark text-white'
                  : 'bg-brand-surface text-brand-dark border border-brand-dark hover:bg-white'
              }`}
            >
              TUTTI ({tenders.length})
            </button>

            <button
              onClick={() => {
                setScoreFilter(scoreFilter === 'qualified' ? 'all' : 'qualified');
              }}
              className={`px-2.5 py-1 text-xs font-bold font-mono transition-none ${
                scoreFilter === 'qualified'
                  ? 'bg-emerald-600 text-white'
                  : 'bg-brand-surface text-brand-dark border border-brand-dark hover:bg-white'
              }`}
            >
              ALTA PRIORITÀ (≥45)
            </button>

            <button
              onClick={() => {
                setDistanceFilter(distanceFilter === '40' ? 'all' : '40');
              }}
              className={`px-2.5 py-1 text-xs font-bold font-mono transition-none ${
                distanceFilter === '40'
                  ? 'bg-brand-accent text-white'
                  : 'bg-brand-surface text-brand-dark border border-brand-dark hover:bg-white'
              }`}
            >
              MARGHINE/40KM
            </button>

            <button
              onClick={() => setCmeOnlyFilter(!cmeOnlyFilter)}
              className={`px-2.5 py-1 text-xs font-bold font-mono transition-none ${
                cmeOnlyFilter
                  ? 'bg-brand-dark text-white'
                  : 'bg-brand-surface text-brand-dark border border-brand-dark hover:bg-white'
              }`}
            >
              CME ANALIZZATO
            </button>

            <button
              onClick={() => {
                setStatusFilter(statusFilter === 'da_chiamare' ? 'all' : 'da_chiamare');
              }}
              className={`px-2.5 py-1 text-xs font-bold font-mono transition-none ${
                statusFilter === 'da_chiamare'
                  ? 'bg-slate-700 text-white'
                  : 'bg-brand-surface text-brand-dark border border-brand-dark hover:bg-white'
              }`}
            >
              DA CONTATTARE
            </button>
          </div>

          {/* Compact Sort Selector */}
          <div className="flex items-center gap-1 font-mono text-xs">
            <span className="text-brand-muted text-[11px] uppercase font-bold">ORDINA:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortField)}
              className="bg-brand-surface border border-brand-dark px-2 py-1 text-xs font-bold text-brand-dark focus:outline-none"
            >
              <option value="score">Score</option>
              <option value="amount">Importo</option>
              <option value="distance">Distanza</option>
              <option value="date">Data</option>
            </select>
            <button
              onClick={() => setSortAsc(!sortAsc)}
              className="p-1 bg-brand-surface border border-brand-dark text-brand-dark hover:bg-brand-dark hover:text-white transition-none"
              title="Inverti ordinamento"
            >
              <ArrowUpDown className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* DESKTOP VIEW (High-density Monolithic Table) */}
      <div className="hidden lg:block bg-white border-2 border-brand-dark shadow-none overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-brand-dark text-white font-mono uppercase text-[11px] border-b-2 border-brand-dark select-none">
              <th className="py-2.5 px-3 w-16 text-center">Score</th>
              <th className="py-2.5 px-3 w-28 text-center">Distanza</th>
              <th className="py-2.5 px-3 w-32">CIG / ID</th>
              <th className="py-2.5 px-3">Oggetto Appalto & Località</th>
              <th className="py-2.5 px-3 w-36">Importo Gara</th>
              <th className="py-2.5 px-3 w-44">Impresa / Subappalto</th>
              <th className="py-2.5 px-3 w-36 text-center">Stato CRM</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-brand-border">
            {filteredTenders.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-12 text-center text-brand-muted text-sm font-mono">
                  Nessun bando trovato corrispondente ai filtri selezionati.
                </td>
              </tr>
            ) : (
              filteredTenders.map((tender) => {
                const formattedAmt = tender.amount_eur
                  ? new Intl.NumberFormat('it-IT', {
                      style: 'currency',
                      currency: 'EUR',
                      maximumFractionDigits: 0,
                    }).format(tender.amount_eur)
                  : 'N.D.';

                return (
                  <tr
                    key={tender.dedup_key}
                    className="hover:bg-brand-surface/80 transition-none cursor-pointer group"
                    onClick={() => setSelectedTender(tender)}
                  >
                    {/* Score */}
                    <td className="py-3 px-3 text-center align-middle font-mono font-bold tabular-nums">
                      <span
                        className={`inline-block px-1.5 py-0.5 text-xs font-black ${
                          tender.score >= 45
                            ? 'bg-emerald-600 text-white'
                            : 'bg-brand-surface text-brand-dark border border-brand-border'
                        }`}
                      >
                        {Math.round(tender.score)}
                      </span>
                    </td>

                    {/* Distanza Silanus */}
                    <td className="py-3 px-3 text-center align-middle font-mono text-[11px] tabular-nums">
                      {tender.site_distance_km !== null ? (
                        <span
                          className={`font-bold ${
                            tender.site_distance_km <= 40
                              ? 'text-brand-accent font-black'
                              : 'text-brand-ink'
                          }`}
                        >
                          ~{tender.site_distance_km} km
                        </span>
                      ) : (
                        <span className="text-brand-muted">N.D.</span>
                      )}
                    </td>

                    {/* CIG */}
                    <td className="py-3 px-3 align-middle font-mono tabular-nums">
                      <span className="font-bold text-brand-dark block text-xs">
                        {tender.cig || 'In attesa'}
                      </span>
                      <span className="text-[10px] text-brand-muted font-mono uppercase tracking-wider">
                        {tender.source === 'bdap'
                          ? 'BDAP / ANAC'
                          : tender.source === 'telemat'
                          ? 'TELEMAT SARDEGNA'
                          : tender.source === 'sardegnacat'
                          ? 'SARDEGNA_CAT'
                          : tender.source === 'invitalia'
                          ? 'INVITALIA'
                          : tender.source === 'anac'
                          ? 'ANAC'
                          : tender.source.toUpperCase()}
                      </span>
                    </td>

                    {/* Title & Comune */}
                    <td className="py-3 px-3 align-middle">
                      <div className="font-bold text-brand-dark line-clamp-2 leading-snug group-hover:text-brand-accent">
                        {tender.title}
                      </div>
                      <div className="flex items-center gap-2 mt-1 text-[11px] text-brand-muted">
                        <span className="font-bold text-brand-ink flex items-center gap-1">
                          <MapPin className="w-3 h-3 text-brand-dark" />
                          {tender.municipality || 'Regione Sardegna'} ({tender.province})
                        </span>
                        <span>•</span>
                        <span className="truncate max-w-[200px]">
                          {tender.contracting_authority}
                        </span>
                      </div>
                    </td>

                    {/* Importo */}
                    <td className="py-3 px-3 align-middle font-mono font-bold text-brand-dark text-xs tabular-nums">
                      {formattedAmt}
                    </td>

                    {/* Impresa */}
                    <td className="py-3 px-3 align-middle">
                      {tender.winner_company ? (
                        <div>
                          <span className="font-bold text-brand-ink block truncate max-w-[170px]">
                            {tender.winner_company}
                          </span>
                          {tender.winner_tax_id && (
                            <span className="text-[10px] font-mono text-brand-muted tabular-nums">
                              P.IVA: {tender.winner_tax_id}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-brand-muted italic text-[11px]">
                          Gara in affidamento
                        </span>
                      )}
                    </td>

                    {/* Stato CRM */}
                    <td
                      className="py-3 px-3 text-center align-middle"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <select
                        value={tender.crm_status}
                        onChange={(e) =>
                          handleStatusUpdate(
                            tender.dedup_key,
                            e.target.value as CrmStatus
                          )
                        }
                        className="bg-brand-surface border border-brand-dark text-[10px] font-mono font-bold py-1 px-1.5 focus:outline-none"
                      >
                        <option value="da_chiamare">DA CONTATTARE</option>
                        <option value="preventivo_inviato">OFFERTA INVIATA</option>
                        <option value="vinto">VINTO</option>
                        <option value="scartato">SCARTATO</option>
                      </select>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* MOBILE / TABLET VIEW (Industrial Card Slabs for Field / Cantiere) */}
      <div className="lg:hidden space-y-3">
        {filteredTenders.length === 0 ? (
          <div className="bg-white border-2 border-brand-dark p-8 text-center text-brand-muted text-xs font-mono">
            Nessun bando trovato corrispondente ai filtri selezionati.
          </div>
        ) : (
          filteredTenders.map((tender) => {
            const formattedAmt = tender.amount_eur
              ? new Intl.NumberFormat('it-IT', {
                  style: 'currency',
                  currency: 'EUR',
                  maximumFractionDigits: 0,
                }).format(tender.amount_eur)
              : 'N.D.';

            return (
              <div
                key={tender.dedup_key}
                onClick={() => setSelectedTender(tender)}
                className="bg-white border-2 border-brand-dark p-4 space-y-3 shadow-none active:bg-brand-surface transition-none cursor-pointer"
              >
                {/* Header Card: Score & Distance & Status */}
                <div className="flex items-center justify-between border-b border-brand-border/40 pb-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`font-mono text-xs font-black px-2 py-0.5 tabular-nums ${
                        tender.score >= 45
                          ? 'bg-emerald-600 text-white'
                          : 'bg-brand-dark text-white'
                      }`}
                    >
                      SCORE {Math.round(tender.score)}
                    </span>

                    {tender.site_distance_km !== null && (
                      <span className="font-mono text-xs font-bold text-brand-dark px-1.5 py-0.5 bg-brand-surface border border-brand-dark tabular-nums">
                        ~{tender.site_distance_km} km Silanus
                      </span>
                    )}
                  </div>

                  <div>{getStatusBadge(tender.crm_status)}</div>
                </div>

                {/* Title */}
                <div>
                  <h3 className="font-bold text-sm text-brand-dark leading-snug">
                    {tender.title}
                  </h3>
                  <div className="flex items-center gap-2 mt-1.5 text-xs text-brand-muted font-medium">
                    <MapPin className="w-3.5 h-3.5 text-brand-dark shrink-0" />
                    <span>
                      {tender.municipality || 'Sardegna'} ({tender.province})
                    </span>
                    <span>•</span>
                    <span className="font-mono text-[10px] uppercase">
                      {tender.source === 'bdap'
                        ? 'BDAP / ANAC'
                        : tender.source === 'telemat'
                        ? 'TELEMAT'
                        : tender.source === 'sardegnacat'
                        ? 'SARDEGNA_CAT'
                        : tender.source === 'invitalia'
                        ? 'INVITALIA'
                        : tender.source === 'anac'
                        ? 'ANAC'
                        : tender.source.toUpperCase()}
                    </span>
                  </div>
                </div>

                {/* Key Numbers */}
                <div className="grid grid-cols-2 gap-2 bg-brand-surface border border-brand-border p-2.5 text-xs">
                  <div>
                    <span className="block text-[10px] uppercase font-bold text-brand-muted">
                      Importo Gara
                    </span>
                    <span className="font-mono font-bold text-brand-dark tabular-nums">
                      {formattedAmt}
                    </span>
                  </div>

                  <div>
                    <span className="block text-[10px] uppercase font-bold text-brand-muted">
                      Codice CIG
                    </span>
                    <span className="font-mono font-bold text-brand-dark tabular-nums">
                      {tender.cig || 'In attesa'}
                    </span>
                  </div>
                </div>

                {/* Contractor if present */}
                {tender.winner_company && (
                  <div className="text-xs pt-1">
                    <span className="block text-[10px] uppercase font-bold text-brand-muted">
                      Aggiudicatario:
                    </span>
                    <span className="font-bold text-brand-ink">
                      {tender.winner_company}
                    </span>
                    {tender.winner_tax_id && (
                      <span className="block text-[10px] font-mono text-brand-muted tabular-nums">
                        P.IVA: {tender.winner_tax_id}
                      </span>
                    )}
                  </div>
                )}

                {/* Open Drawer CTA Button */}
                <button
                  onClick={() => setSelectedTender(tender)}
                  className="w-full flex items-center justify-center gap-2 bg-brand-dark text-white py-2.5 text-xs font-bold uppercase tracking-wider hover:bg-brand-border transition-none min-h-[44px]"
                >
                  Dettagli, Voci CME & Bozza PEC <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* Drawer */}
      <LeadDrawer
        tender={selectedTender}
        onClose={() => setSelectedTender(null)}
        onStatusUpdate={handleStatusUpdate}
      />
    </div>
  );
}

'use client';

import React, { useEffect, useState, useTransition } from 'react';
import type { TenderRow, CmeItemRow, CrmStatus } from '@/lib/types';
import { getCmeItemsForTender } from '@/app/actions/crm-actions';
import {
  generatePecDraft,
  classifyPhoneNumber,
  generateWhatsAppMessage,
} from '@/lib/quick-actions';
import {
  X,
  Copy,
  Check,
  MessageSquare,
  Phone,
  ExternalLink,
  MapPin,
  Building,
  Layers,
  Save,
  Loader2,
} from 'lucide-react';

interface LeadDrawerProps {
  tender: TenderRow | null;
  onClose: () => void;
  onStatusUpdate: (dedupKey: string, status: CrmStatus, notes: string) => Promise<void>;
}

export default function LeadDrawer({
  tender,
  onClose,
  onStatusUpdate,
}: LeadDrawerProps) {
  const [cmeItems, setCmeItems] = useState<CmeItemRow[]>([]);
  const [loadingCme, setLoadingCme] = useState(false);
  const [status, setStatus] = useState<CrmStatus>('da_chiamare');
  const [notes, setNotes] = useState('');
  const [isSaving, startSavingTransition] = useTransition();
  const [copiedPec, setCopiedPec] = useState(false);

  useEffect(() => {
    if (tender) {
      setStatus(tender.crm_status || 'da_chiamare');
      setNotes(tender.crm_notes || '');
      setCopiedPec(false);

      // Lazy fetch CME items
      setLoadingCme(true);
      getCmeItemsForTender(tender.dedup_key)
        .then((items) => setCmeItems(items))
        .catch((err) => {
          console.error('Failed to load CME items:', err);
          setCmeItems([]);
        })
        .finally(() => setLoadingCme(false));
    } else {
      setCmeItems([]);
    }
  }, [tender]);

  if (!tender) return null;

  const handleCopyPec = async () => {
    const { body } = generatePecDraft({ tender, cmeItems });
    try {
      await navigator.clipboard.writeText(body);
      setCopiedPec(true);
      setTimeout(() => setCopiedPec(false), 2500);
    } catch {
      alert('Impossibile copiare negli appunti automaticamente.');
    }
  };

  const handleSaveCrm = () => {
    startSavingTransition(async () => {
      await onStatusUpdate(tender.dedup_key, status, notes);
    });
  };

  const formattedAmount = tender.amount_eur
    ? new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(
        tender.amount_eur
      )
    : 'Importo non dichiarato';

  const phoneInfo = classifyPhoneNumber(
    tender.payload?.notice?.winner_company_phone || null,
    generateWhatsAppMessage(tender)
  );

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-brand-dark/60 backdrop-blur-none transition-none animate-in fade-in duration-100">
      {/* Backdrop click area */}
      <div className="absolute inset-0" onClick={onClose} />

      {/* Drawer Container */}
      <div className="relative w-full max-w-2xl bg-white border-l-4 border-brand-dark flex flex-col h-full shadow-none z-10 overflow-hidden">
        {/* Drawer Header */}
        <div className="bg-brand-dark text-white p-4 flex items-center justify-between border-b-2 border-brand-border shrink-0">
          <div className="flex items-center gap-3">
            <span className="font-mono text-xs px-2 py-1 bg-brand-accent text-white font-bold tracking-wider">
              {tender.cig ? `CIG: ${tender.cig}` : 'CIG: ASSENTE / IN ATTESA'}
            </span>
            <span
              className={`font-mono text-xs px-2 py-1 font-bold ${
                tender.score >= 45
                  ? 'bg-emerald-600 text-white'
                  : 'bg-brand-border text-white'
              }`}
            >
              SCORE: {Math.round(tender.score)}/100
            </span>
          </div>

          <button
            onClick={onClose}
            className="p-2 text-white hover:bg-brand-border transition-none flex items-center justify-center min-w-[44px] min-h-[44px]"
            title="Chiudi pannello (Esc)"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6 bg-brand-surface">
          {/* Title & Ente */}
          <div className="bg-white border-2 border-brand-dark p-4 space-y-3">
            <h2 className="text-base md:text-lg font-bold text-brand-dark font-sans leading-snug">
              {tender.title}
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs pt-2 border-t border-brand-border/30">
              <div className="flex items-start gap-2 text-brand-muted">
                <Building className="w-4 h-4 text-brand-dark shrink-0 mt-0.5" />
                <div>
                  <span className="block font-bold text-brand-ink uppercase text-[10px]">
                    Ente Appaltante
                  </span>
                  <span>{tender.contracting_authority}</span>
                </div>
              </div>

              <div className="flex items-start gap-2 text-brand-muted">
                <MapPin className="w-4 h-4 text-brand-dark shrink-0 mt-0.5" />
                <div>
                  <span className="block font-bold text-brand-ink uppercase text-[10px]">
                    Località & Distanza da Silanus
                  </span>
                  <span className="font-bold text-brand-dark">
                    {tender.municipality || 'Comune non specificato'} ({tender.province})
                  </span>
                  {tender.site_distance_km !== null && (
                    <span className="block font-mono text-[11px] text-brand-accent">
                      ~{tender.site_distance_km} km da Silanus (NU)
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-brand-border/30 flex items-center justify-between">
              <div>
                <span className="text-[10px] uppercase font-bold text-brand-muted block">
                  Importo Gara
                </span>
                <span className="font-mono text-base font-black text-brand-dark">
                  {formattedAmount}
                </span>
              </div>

              {tender.url && (
                <a
                  href={tender.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs font-bold text-brand-dark hover:text-brand-accent underline underline-offset-4"
                >
                  Bando Ufficiale <ExternalLink className="w-3.5 h-3.5" />
                </a>
              )}
            </div>
          </div>

          {/* Winner Contractor Info */}
          <div className="bg-white border-2 border-brand-dark p-4 space-y-3">
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-brand-dark border-b border-brand-border/30 pb-2">
              Impresa Aggiudicataria / Subappalto
            </h3>

            {tender.winner_company ? (
              <div className="space-y-2">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-1">
                  <span className="font-bold text-sm text-brand-ink">
                    {tender.winner_company}
                  </span>
                  {tender.winner_tax_id && (
                    <span className="font-mono text-xs text-brand-muted">
                      P.IVA/CF: {tender.winner_tax_id}
                    </span>
                  )}
                </div>

                <div className="flex flex-wrap gap-2 pt-2">
                  {tender.winner_tax_id && (
                    <a
                      href={`https://www.registroimprese.it/ricerca-libera-e-acquisto?ricerca=${encodeURIComponent(
                        tender.winner_tax_id
                      )}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-2 py-1 bg-brand-surface border border-brand-dark text-[11px] font-bold text-brand-dark hover:bg-brand-dark hover:text-white transition-none"
                    >
                      Verifica INI-PEC Registro Imprese ↗
                    </a>
                  )}

                  <a
                    href={`https://www.google.com/search?q=${encodeURIComponent(
                      `${tender.winner_company} PEC contatti Sardegna`
                    )}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-2 py-1 bg-brand-surface border border-brand-dark text-[11px] font-bold text-brand-dark hover:bg-brand-dark hover:text-white transition-none"
                  >
                    Cerca Contatti su Google ↗
                  </a>
                </div>
              </div>
            ) : (
              <p className="text-xs text-brand-muted italic">
                Nessuna impresa aggiudicataria ancora registrata (gara in corso di affidamento).
              </p>
            )}
          </div>

          {/* CME Breakdown (Computo Metrico) */}
          <div className="bg-white border-2 border-brand-dark p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-brand-border/30 pb-2">
              <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-brand-dark flex items-center gap-1.5">
                <Layers className="w-4 h-4 text-brand-accent" />
                Voci Computo Metrico Rilevate ({cmeItems.length})
              </h3>
              {loadingCme && <Loader2 className="w-4 h-4 animate-spin text-brand-dark" />}
            </div>

            {loadingCme ? (
              <div className="py-6 text-center text-xs text-brand-muted">
                Caricamento voci computo in corso...
              </div>
            ) : cmeItems.length > 0 ? (
              <div className="space-y-2">
                <div className="max-h-60 overflow-y-auto border border-brand-border divide-y divide-brand-border">
                  {cmeItems.map((item, idx) => (
                    <div key={idx} className="p-2.5 text-xs bg-white space-y-1">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="font-mono font-bold text-brand-dark">
                          {item.tariff_code || `Voce #${idx + 1}`}
                        </span>
                        <span className="px-1.5 py-0.5 bg-brand-surface font-semibold text-[10px] text-brand-muted border border-brand-border/50">
                          {item.product_line === 'linea_a' ? 'Linea A (CAV)' : 'Linea B (Rivendita)'}
                        </span>
                      </div>
                      <p className="text-brand-ink font-medium leading-relaxed">
                        {item.description}
                      </p>
                      <div className="flex items-center gap-3 text-[11px] font-mono text-brand-muted">
                        <span>
                          Q.tà: <strong className="text-brand-ink">{item.quantity}</strong> {item.unit}
                        </span>
                        {item.total_price_eur !== null && (
                          <span>
                            Totale: <strong>€{item.total_price_eur.toFixed(2)}</strong>
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-xs text-brand-muted italic py-2">
                Nessun file CME estratto o allegato per questo bando.
              </p>
            )}
          </div>

          {/* CRM State & Notes */}
          <div className="bg-white border-2 border-brand-dark p-4 space-y-3">
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-brand-dark border-b border-brand-border/30 pb-2">
              Gestione Commerciale Lead
            </h3>

            <div className="space-y-3">
              <div>
                <label className="block text-[11px] font-bold text-brand-muted uppercase mb-1">
                  Stato Avanzamento Trattativa
                </label>
                <select
                  value={status}
                  onChange={(e) => setStatus(e.target.value as CrmStatus)}
                  className="w-full bg-brand-surface border-2 border-brand-dark px-3 py-2 text-xs font-bold text-brand-dark focus:outline-none focus:ring-2 focus:ring-brand-accent transition-none"
                >
                  <option value="da_chiamare">DA CONTATTARE</option>
                  <option value="preventivo_inviato">PREVENTIVO INVIATO</option>
                  <option value="vinto">FORNITURA ACQUISITA (VINTO)</option>
                  <option value="scartato">SCARTATO / NON INTERESSATO</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-brand-muted uppercase mb-1">
                  Note Interne (Cantiere / Riferimenti)
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={3}
                  placeholder="Es. Contattato geom. Puddu via WhatsApp il 24/11. Richiesta offerta per 45 pozzetti 80x80 con consegna cantiere Gavoi."
                  className="w-full bg-brand-surface border-2 border-brand-dark p-2 text-xs text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-accent transition-none"
                />
              </div>

              <button
                onClick={handleSaveCrm}
                disabled={isSaving}
                className="w-full flex items-center justify-center gap-2 bg-brand-dark text-white px-4 py-2.5 text-xs font-bold uppercase tracking-wider hover:bg-brand-border transition-none disabled:opacity-50 min-h-[44px]"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> Salvataggio...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" /> Salva Note & Stato CRM
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Sticky Action Bar */}
        <div className="sticky bottom-0 bg-brand-surface border-t-4 border-brand-dark p-3 md:p-4 shrink-0 flex flex-col sm:flex-row gap-2 z-20">
          <button
            onClick={handleCopyPec}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 text-xs md:text-sm font-bold uppercase tracking-wider transition-none min-h-[48px] ${
              copiedPec
                ? 'bg-emerald-600 text-white'
                : 'bg-brand-dark text-white hover:bg-brand-border'
            }`}
          >
            {copiedPec ? (
              <>
                <Check className="w-4 h-4" /> Bozza PEC Copiata!
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" /> Copia Bozza PEC
              </>
            )}
          </button>

          {phoneInfo.type === 'whatsapp' && phoneInfo.whatsappUrl ? (
            <a
              href={phoneInfo.whatsappUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-[#25D366] text-white text-xs md:text-sm font-bold uppercase tracking-wider hover:opacity-90 transition-none min-h-[48px]"
            >
              <MessageSquare className="w-4 h-4" /> WhatsApp Rapido
            </a>
          ) : phoneInfo.type === 'call' && phoneInfo.callUrl ? (
            <a
              href={phoneInfo.callUrl}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-brand-border text-white text-xs md:text-sm font-bold uppercase tracking-wider hover:bg-brand-dark transition-none min-h-[48px]"
            >
              <Phone className="w-4 h-4" /> Chiama Impresa ({phoneInfo.cleanNumber})
            </a>
          ) : (
            <a
              href={`https://wa.me/?text=${encodeURIComponent(
                generateWhatsAppMessage(tender)
              )}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-white border-2 border-brand-dark text-brand-dark text-xs md:text-sm font-bold uppercase tracking-wider hover:bg-brand-dark hover:text-white transition-none min-h-[48px]"
            >
              <MessageSquare className="w-4 h-4" /> Condividi WhatsApp
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

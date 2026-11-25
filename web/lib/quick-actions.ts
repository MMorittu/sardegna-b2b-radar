import type { TenderRow, CmeItemRow } from './types';

/**
 * Strips carriage returns and newlines from dynamic header fields to prevent CRLF injection.
 */
export function sanitizeHeaderField(input: string | null | undefined): string {
  if (!input) return '';
  return input.replace(/[\r\n]+/g, ' ').trim();
}

export interface PecDraftOptions {
  tender: TenderRow;
  cmeItems?: CmeItemRow[];
}

/**
 * Generates an official B2B sub-supply quotation draft.
 * Formatted ready to be pasted into Aruba PEC, Legalmail, or email client.
 */
export function generatePecDraft({ tender, cmeItems = [] }: PecDraftOptions): {
  subject: string;
  body: string;
} {
  const companyName = process.env.NEXT_PUBLIC_COMPANY_NAME || 'Divisione Subforniture Industriali';
  const companyPec = process.env.NEXT_PUBLIC_COMPANY_PEC || 'commerciale@azienda.pec.it';
  const companyPhone = process.env.NEXT_PUBLIC_COMPANY_PHONE || '+39 070 1234567';
  const companyPiva = process.env.NEXT_PUBLIC_COMPANY_PIVA || '00000000000';
  const companyLocation = process.env.NEXT_PUBLIC_COMPANY_LOCATION || 'Sardegna';

  const cleanCig = sanitizeHeaderField(tender.cig) || 'in fase di perfezionamento';
  const cleanCup = sanitizeHeaderField(tender.cup);
  const cleanComune = sanitizeHeaderField(tender.municipality) || sanitizeHeaderField(tender.province) || 'Sardegna';
  const cleanCompany = sanitizeHeaderField(tender.winner_company) || 'Spett.le Impresa Aggiudicataria';
  const cleanTitle = sanitizeHeaderField(tender.title);

  // Group detected CME categories if available
  const detectedCategories = Array.from(
    new Set(
      cmeItems
        .map((it) => it.matched_catalog_label || it.category)
        .filter(Boolean)
    )
  );

  const subject = `Offerta Subfornitura Manufatti C.A.V. & Materiali Edili — Gara CIG: ${cleanCig} (${cleanComune})`;

  const itemsList =
    detectedCategories.length > 0
      ? detectedCategories.map((c) => `  • ${c}`).join('\n')
      : '  • Pozzetti, prolunghe, chiusini e caditoie in C.A.V. (UNI EN 1917)\n  • Cordonate e cordoli stradali / marciapiedi (UNI EN 1340)\n  • Tubazioni e manufatti prefabbricati speciali';

  const body = `Alla c.a. Ufficio Acquisti e Direzione Tecnica
${cleanCompany}

Oggetto: Proposta di subfornitura manufatti in cemento e materiali da cantiere
Gara: ${cleanTitle}
CIG: ${cleanCig}${cleanCup ? ` | CUP: ${cleanCup}` : ''}
Luogo esecuzione lavori: ${cleanComune}

Gentili Signori,

in merito ai lavori in oggetto di recente affidamento presso il Comune di ${cleanComune}, con la presente ${companyName} (${companyLocation}) desidera sottoporre la propria migliore offerta per la fornitura diretta in cantiere dei seguenti manufatti ed articoli rilevati da capitolato:

${itemsList}

PUNTI DI FORZA LOGISTICI & OPERATIVI:
1. Produzione e fornitura manufatti C.A.V. certificati a norme UNI EN vigenti.
2. Consegna con mezzi propri dotati di autogru direttamente a piè d'opera in tutta la Sardegna.
3. Tempestività di fornitura e coordinamento logistico con la direzione di cantiere.
4. Completa disponibilità a magazzino di ferro lavorato B450C, inerti, tubazioni fognatura PVC SN4/SN8 e malte tecniche di ripristino.

Restiamo a Vs. completa disposizione per quotare senza impegno il computo metrico dettagliato o concordare un sopralluogo congiunto in cantiere.

In attesa di un Vs. cortese riscontro, porgiamo distinti saluti.

${companyName}
Ufficio Commerciale & Gare — ${companyLocation}
P.IVA: ${companyPiva} | Tel: ${companyPhone}
Email PEC: ${companyPec}
`;

  return { subject, body };
}

export interface PhoneClassification {
  raw: string;
  cleanNumber: string;
  isMobile: boolean;
  type: 'whatsapp' | 'call' | 'none';
  whatsappUrl: string | null;
  callUrl: string | null;
}

/**
 * Classifies an Italian phone number and creates dynamic actions (WhatsApp vs Voice Call).
 */
export function classifyPhoneNumber(rawPhone: string | null | undefined, message: string = ''): PhoneClassification {
  if (!rawPhone) {
    return {
      raw: '',
      cleanNumber: '',
      isMobile: false,
      type: 'none',
      whatsappUrl: null,
      callUrl: null,
    };
  }

  // Strip non-digit characters except leading +
  let clean = rawPhone.trim().replace(/[\s\-\/\.\(\)]+/g, '');
  if (clean.startsWith('+39')) {
    clean = clean.slice(3);
  } else if (clean.startsWith('0039')) {
    clean = clean.slice(4);
  }

  // In Italy:
  // Mobile numbers start with '3' (length 9-10 digits, e.g. 3401234567)
  // Landline numbers start with '0' (e.g. 078584123)
  const isMobile = clean.startsWith('3') && clean.length >= 9 && clean.length <= 11;
  const isLandline = clean.startsWith('0') && clean.length >= 7 && clean.length <= 12;

  const encodedMsg = encodeURIComponent(message);
  const whatsappUrl = isMobile ? `https://wa.me/39${clean}${message ? `?text=${encodedMsg}` : ''}` : null;
  const callUrl = isMobile || isLandline ? `tel:+39${clean}` : null;

  return {
    raw: rawPhone,
    cleanNumber: clean,
    isMobile,
    type: isMobile ? 'whatsapp' : isLandline ? 'call' : 'none',
    whatsappUrl,
    callUrl,
  };
}

/**
 * Generates an instant WhatsApp message for awarded contractor outreach.
 */
export function generateWhatsAppMessage(tender: TenderRow): string {
  const companyName = process.env.NEXT_PUBLIC_COMPANY_NAME || 'Ufficio Commerciale';
  const cleanCig = sanitizeHeaderField(tender.cig) || 'gara in corso';
  const cleanComune = sanitizeHeaderField(tender.municipality) || 'Sardegna';

  return `Buongiorno, vi contatto da ${companyName}. Vi scrivo in merito all'appalto di ${cleanComune} (CIG ${cleanCig}) per proporvi fornitura e consegna con autogru di pozzetti, chiusini e cordoli a piè d'opera. Possiamo inviarvi una quotazione rapida? Grazie.`;
}

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  sanitizeHeaderField,
  classifyPhoneNumber,
  generatePecDraft,
  generateWhatsAppMessage,
} from '../lib/quick-actions.ts';
import type { TenderRow, CmeItemRow } from '../lib/types.ts';

describe('Quick Actions - sanitizeHeaderField', () => {
  test('strips carriage returns, newlines, tabs, and trims whitespace', () => {
    assert.strictEqual(sanitizeHeaderField('Hello\r\nWorld'), 'Hello World');
    assert.strictEqual(sanitizeHeaderField('\r\n  Iniezione\r\nHeader  \t'), 'Iniezione Header');
    assert.strictEqual(sanitizeHeaderField(''), '');
    assert.strictEqual(sanitizeHeaderField(null), '');
    assert.strictEqual(sanitizeHeaderField(undefined), '');
  });
});

describe('Quick Actions - classifyPhoneNumber', () => {
  test('classifies standard Italian mobile numbers and creates wa.me link', () => {
    const res = classifyPhoneNumber('340 1234567', 'Ciao cantiere');
    assert.strictEqual(res.isMobile, true);
    assert.strictEqual(res.type, 'whatsapp');
    assert.strictEqual(res.cleanNumber, '3401234567');
    assert.strictEqual(
      res.whatsappUrl,
      'https://wa.me/393401234567?text=Ciao%20cantiere'
    );
    assert.strictEqual(res.callUrl, 'tel:+393401234567');
  });

  test('normalizes +39 and 0039 prefixes for mobile numbers', () => {
    const plus39 = classifyPhoneNumber('+39 349 9876543');
    assert.strictEqual(plus39.isMobile, true);
    assert.strictEqual(plus39.cleanNumber, '3499876543');
    assert.strictEqual(plus39.whatsappUrl, 'https://wa.me/393499876543');

    const doubleZero = classifyPhoneNumber('0039-333-1122334');
    assert.strictEqual(doubleZero.isMobile, true);
    assert.strictEqual(doubleZero.cleanNumber, '3331122334');
  });

  test('classifies Italian landlines (starting with 0) as call-only', () => {
    const landline = classifyPhoneNumber('0785/84123');
    assert.strictEqual(landline.isMobile, false);
    assert.strictEqual(landline.type, 'call');
    assert.strictEqual(landline.cleanNumber, '078584123');
    assert.strictEqual(landline.whatsappUrl, null);
    assert.strictEqual(landline.callUrl, 'tel:+39078584123');
  });

  test('returns safe fallback for empty or null numbers', () => {
    const empty = classifyPhoneNumber('');
    assert.strictEqual(empty.type, 'none');
    assert.strictEqual(empty.whatsappUrl, null);
    assert.strictEqual(empty.callUrl, null);

    const nullVal = classifyPhoneNumber(null);
    assert.strictEqual(nullVal.type, 'none');
  });
});

describe('Quick Actions - generatePecDraft', () => {
  const mockTender: TenderRow = {
    dedup_key: 'test-tender-1',
    source: 'ANAC',
    external_id: 'EXT-123',
    notice_type: 'appalto_lavori',
    cig: 'B123456789',
    cup: 'C12E23000010004',
    title: 'Lavori di riqualificazione urbana e sottoservizi',
    contracting_authority: 'Comune di Silanus',
    delegated_authority: null,
    province: 'NU',
    municipality: 'Silanus',
    site_distance_km: 0,
    amount_eur: 250000,
    award_amount_eur: 220000,
    discount_pct: 12.0,
    published_date: '2026-11-20',
    deadline_date: '2026-12-15',
    award_date: '2026-11-22',
    winner_company: 'Costruzioni Sarde S.r.l.',
    winner_tax_id: '01234567890',
    winner_province: 'NU',
    winner_distance_km: 0,
    rup_name: 'Ing. Mario Rossi',
    contract_started: true,
    has_subcontracts: true,
    score: 85,
    logistics_tier: 'tier_1_40km',
    crm_status: 'da_chiamare',
    crm_notes: '',
    cme_fetch_status: 'fetched',
    notified: false,
    url: 'https://example.com/bando',
    attachment_url: null,
    http_status: 200,
    discovered_at: '2026-11-20T10:00:00Z',
  };

  test('generates valid PEC subject and body containing company credentials', () => {
    const draft = generatePecDraft({ tender: mockTender });
    assert.ok(draft.subject.includes('B123456789'));
    assert.ok(draft.subject.includes('Silanus'));
    assert.ok(draft.body.includes('Costruzioni Sarde S.r.l.'));
    assert.ok(draft.body.includes('Alla c.a. Ufficio Acquisti e Direzione Tecnica'));
    assert.ok(draft.body.includes('PUNTI DI FORZA LOGISTICI & OPERATIVI:'));
    assert.ok(draft.body.includes('Ufficio Commerciale & Gare'));
  });

  test('includes detected CME categories when provided', () => {
    const mockCme: CmeItemRow[] = [
      {
        id: 1,
        dedup_key: 'test-tender-1',
        item_seq: 1,
        item_number: 1,
        tariff_code: '01.02.03',
        description: 'Fornitura e posa in opera pozzetto prefabbricato 80x80 in C.A.V.',
        unit: 'cad',
        quantity: 15,
        unit_price_eur: 120.0,
        total_price_eur: 1800.0,
        product_line: 'linea_a',
        category: 'pozzetti_cav',
        matched_catalog_label: 'Pozzetti e prolunghe C.A.V. 80x80',
      },
    ];

    const draft = generatePecDraft({ tender: mockTender, cmeItems: mockCme });
    assert.ok(draft.body.includes('Pozzetti e prolunghe C.A.V. 80x80'));
  });
});

describe('Quick Actions - generateWhatsAppMessage', () => {
  test('generates tailored WhatsApp message with municipality and CIG', () => {
    const msg = generateWhatsAppMessage({
      cig: '9876543210',
      municipality: 'Macomer',
    } as TenderRow);

    assert.ok(msg.includes('Macomer'));
    assert.ok(msg.includes('9876543210'));
    assert.ok(msg.includes('pozzetti, chiusini e cordoli'));
  });
});

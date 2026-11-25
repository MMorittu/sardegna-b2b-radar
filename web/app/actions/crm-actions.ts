'use server';

import { z } from 'zod';
import { revalidatePath } from 'next/cache';
import { headers } from 'next/headers';
import { adminClient } from '@/lib/supabase/admin';
import { checkRateLimit, getClientIp } from '@/lib/rate-limiter';
import { DEMO_CME_ITEMS, DEMO_TENDERS } from '@/lib/demo-data';
import type { CmeItemRow, Database } from '@/lib/types';

const UpdateCrmStatusSchema = z.object({
  dedupKey: z.string().min(3),
  status: z.enum(['da_chiamare', 'preventivo_inviato', 'vinto', 'scartato']),
  notes: z.string().max(2000).optional(),
});

export type UpdateCrmStatusInput = z.infer<typeof UpdateCrmStatusSchema>;

/**
 * Updates CRM pipeline status and commercial notes for a tender by dedup_key.
 * Protected by anti-hammering rate limiter (max 30 status updates/min per IP).
 */
export async function updateTenderCrmStatus(input: UpdateCrmStatusInput) {
  const clientIp = getClientIp(headers());

  if (!checkRateLimit(`crm-update-${clientIp}`, 60 * 1000, 30)) {
    throw new Error('Too many requests. Please wait before updating CRM status.');
  }

  const parsed = UpdateCrmStatusSchema.parse(input);

  if (!adminClient) {
    // Portfolio Demo Mode fallback
    const mockTender = DEMO_TENDERS.find((t) => t.dedup_key === parsed.dedupKey);
    if (mockTender) {
      mockTender.crm_status = parsed.status;
      if (parsed.notes !== undefined) {
        mockTender.crm_notes = parsed.notes;
      }
    }
    revalidatePath('/');
    return { success: true };
  }

  const updatePayload: Database['public']['Tables']['tenders']['Update'] = {
    crm_status: parsed.status,
    updated_at: new Date().toISOString(),
    ...(parsed.notes !== undefined ? { crm_notes: parsed.notes } : {}),
  };

  const { data, error } = await adminClient
    .from('tenders')
    .update(updatePayload)
    .eq('dedup_key', parsed.dedupKey)
    .select('dedup_key');

  if (error) {
    throw new Error(`Errore aggiornamento stato CRM: ${error.message}`);
  }

  if (!data || data.length === 0) {
    throw new Error(`Nessun bando trovato con dedup_key: ${parsed.dedupKey}`);
  }

  revalidatePath('/');
  return { success: true };
}

/**
 * Lazy loads CME (Computo Metrico) items for a given tender.
 * Protected by rate limiter (max 180 CME fetches/min per IP) to allow fluid navigation while preventing pool exhaustion.
 */
export async function getCmeItemsForTender(dedupKey: string): Promise<CmeItemRow[]> {
  if (!dedupKey) {
    return [];
  }

  const clientIp = getClientIp(headers());
  if (!checkRateLimit(`cme-fetch-${clientIp}`, 60 * 1000, 180)) {
    throw new Error('Too many requests. Please wait before fetching CME details.');
  }

  if (!adminClient) {
    // Portfolio Demo Mode fallback
    return DEMO_CME_ITEMS[dedupKey] || [];
  }

  const { data, error } = await adminClient
    .from('cme_items')
    .select('*')
    .eq('dedup_key', dedupKey)
    .order('item_seq', { ascending: true });

  if (error) {
    throw new Error(`Errore caricamento voci CME: ${error.message}`);
  }

  return (data as CmeItemRow[]) || [];
}

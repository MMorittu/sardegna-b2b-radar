export type CrmStatus = 'da_chiamare' | 'preventivo_inviato' | 'vinto' | 'scartato';

export type ProductLine = 'linea_a' | 'linea_b';

export type TenderRow = {
  dedup_key: string;
  source: string;
  external_id: string;
  notice_type: string;
  cig: string | null;
  cup: string | null;
  title: string;
  contracting_authority: string;
  delegated_authority: string | null;
  province: string;
  municipality: string | null;
  site_distance_km: number | null;
  amount_eur: number | null;
  award_amount_eur: number | null;
  discount_pct: number | null;
  published_date: string | null;
  deadline_date: string | null;
  award_date: string | null;
  winner_company: string | null;
  winner_tax_id: string | null;
  winner_province: string | null;
  winner_distance_km: number | null;
  rup_name: string | null;
  contract_started: boolean | null;
  has_subcontracts: boolean | null;
  score: number;
  logistics_tier: string;
  crm_status: CrmStatus;
  crm_notes: string;
  cme_fetch_status: string;
  notified: boolean;
  url: string;
  attachment_url: string | null;
  http_status: number | null;
  payload?: any;
  discovered_at: string;
  updated_at?: string;
};

export type CmeItemRow = {
  id: number;
  dedup_key: string;
  item_seq: number;
  item_number: number | null;
  tariff_code: string;
  description: string;
  unit: string;
  quantity: number;
  unit_price_eur: number | null;
  total_price_eur: number | null;
  product_line: ProductLine;
  category: string;
  matched_catalog_label: string;
};

export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[];

export interface Database {
  public: {
    Tables: {
      tenders: {
        Row: TenderRow;
        Insert: Partial<TenderRow>;
        Update: Partial<TenderRow>;
        Relationships: [];
      };
      cme_items: {
        Row: CmeItemRow;
        Insert: Partial<CmeItemRow>;
        Update: Partial<CmeItemRow>;
        Relationships: [];
      };
    };
    Views: {
      [_ in never]: never;
    };
    Functions: {
      [_ in never]: never;
    };
    Enums: {
      [_ in never]: never;
    };
    CompositeTypes: {
      [_ in never]: never;
    };
  };
}

export interface KpiSummary {
  totalLeads: number;
  totalPipelineEur: number;
  qualifiedLeads: number; // score >= 45
  advantage40kmLeads: number; // site_distance_km <= 40
  byStatus: Record<CrmStatus, number>;
}

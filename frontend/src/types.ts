export type SourceRecord = {
  source_id: string;
  official_domain: string;
  source_url: string;
  source_category: string;
  issuing_authority: string;
  document_type: string;
  ingestion_status: string;
  enabled: boolean;
};

export type Citation = {
  citation_id?: string;
  document_id?: string;
  chunk_id?: string;
  document_title?: string;
  issuing_authority?: string;
  url?: string;
  section_identifier?: string;
  supporting_passage?: string;
  source_version?: string;
  applicable_period?: string;
  provenance_status?: string;
  title?: string;
  authority?: string;
  section?: string;
  passage?: string;
};

export type EvidenceItem = {
  chunk_id?: string;
  document_id?: string;
  document_title?: string;
  source_url?: string;
  issuing_authority?: string;
  section_number?: string;
  text?: string;
  status?: string;
  reasons?: string[];
  metadata?: Record<string, unknown>;
};

export type ChatRequest = {
  question: string;
  tax_year?: string;
  regime?: string;
  conversation_id?: string;
};

export type ChatResponse = {
  conversation_id?: string;
  answer?: string;
  answer_text?: string;
  status?: string;
  tax_period?: string | null;
  citations?: Citation[];
  supporting_evidence?: EvidenceItem[];
  limitations?: string[];
  clarification_question?: string;
  evidence_sufficient?: boolean;
  needs_clarification?: boolean;
  confidence?: string;
  error?: string;
  question?: string;
};

export type ConversationRecord = {
  conversation_id: string;
  title?: string;
  created_at?: string;
  updated_at?: string;
};

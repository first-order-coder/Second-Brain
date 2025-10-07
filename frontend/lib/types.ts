export type Citation = {
  chunk_id: string;
  start_char?: number | null;
  end_char?: number | null;
  score?: number | null;
};

export type SummarySentence = {
  id: string;
  order_index: number;
  sentence_text: string;
  support_status: 'supported' | 'insufficient';
  citations: Citation[];
};

export type Summary = {
  summary_id: string;
  source_id: string;
  sentences: SummarySentence[];
};

 

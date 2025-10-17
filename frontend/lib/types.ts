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

// YouTube-related types for deck parity
export type YouTubeCard = {
  front: string;
  back: string;
  cloze?: string | null;
  start_s?: number | null;
  end_s?: number | null;
  evidence?: string | null;
  difficulty?: "easy" | "medium" | "hard" | null;
  tags?: string[];
};

export type YouTubeFlashcardsResponse = {
  video_id: string;
  title?: string | null;
  url: string;
  lang: string;
  cards: YouTubeCard[];
  warnings: string[];
  deck_id?: string | null; // Added for deck parity
};

 

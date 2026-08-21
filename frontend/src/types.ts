export type ClientConfig = {
  supabase_url: string;
  supabase_publishable_key: string;
};

export type Workspace = { id: string; name: string };

export type Identity = {
  user: { email: string | null; display_name: string | null };
  workspaces: Workspace[];
};

export type DocumentRecord = {
  document_id: string;
  title: string;
  chunks_indexed: number;
  status: string;
};

export type ChatResponse = { answer: string };

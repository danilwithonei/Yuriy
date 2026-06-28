export interface DBMessage {
  sender_role: string;
  content: string;
  timestamp: string;
}

export interface CaseData {
  case: {
    id: string;
    status: string;
    case_file: string | null;
    client_id: number;
    case_type: string;
    title?: string | null;
    summary?: string | null;
  };
  messages: DBMessage[];
}

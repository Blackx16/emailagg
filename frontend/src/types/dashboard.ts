export interface Account {
  id: string;
  provider: "microsoft" | "google" | "imap";
  email: string;
  status: "active" | "syncing" | "error" | "disconnected";
  last_sync: string | null;
  error_message: string | null;
  notify_telegram: boolean;
  deliver_to_dashboard: boolean;
  forward_enabled: boolean;
}

export interface EmailItem {
  id: string;
  mail_account_id: string;
  message_id: string;
  subject: string | null;
  from_email: string | null;
  from_name: string | null;
  received_at: string | null;
  snippet: string | null;
  has_attachment: boolean;
  is_read: boolean;
  body_html?: string | null;
  body_text?: string | null;
}

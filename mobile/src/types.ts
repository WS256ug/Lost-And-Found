export type ReportType = "lost" | "found";
export type ItemStatus = "lost" | "found" | "claimed" | "returned";
export type Category =
  | "electronics"
  | "documents"
  | "id_cards"
  | "keys"
  | "books"
  | "clothing"
  | "other";

export type Profile = {
  role: "student" | "staff";
  phone_number: string | null;
  identification_number: string;
};

export type UserSummary = {
  id: number;
  username: string;
  email: string;
  is_staff: boolean;
};

export type ClaimStatus = "pending" | "approved" | "rejected";

export type Claim = {
  id: number;
  item: Item;
  claimant: UserSummary;
  claimant_profile: Profile | null;
  proof_details: string;
  answer_matches: boolean;
  status: ClaimStatus;
  status_display: string;
  reviewed_by: UserSummary | null;
  reviewed_at: string | null;
  review_note: string;
  created_at: string;
  updated_at: string;
};

export type ClaimSummary = {
  id: number;
  status: ClaimStatus;
  status_display: string;
  answer_matches: boolean;
  review_note: string;
  created_at: string;
  reviewed_at: string | null;
};

export type CurrentUser = UserSummary & {
  profile: Profile | null;
};

export type Item = {
  id: number;
  report_type: ReportType;
  report_type_display: string;
  public_label?: string;
  title?: string;
  description?: string;
  category?: Category;
  category_display?: string;
  location?: string;
  event_date?: string;
  image?: string | null;
  image_url: string | null;
  verification_question?: string;
  has_verification_question?: boolean;
  status: ItemStatus;
  status_display: string;
  reported_by?: UserSummary;
  my_claim?: ClaimSummary | null;
  can_view_private_details?: boolean;
  created_at: string;
  updated_at?: string;
};

export type Message = {
  id: number;
  sender: UserSummary;
  body: string;
  created_at: string;
  is_mine: boolean;
};

export type Conversation = {
  id: number;
  item: Item;
  participant: UserSummary;
  reporter: UserSummary;
  other_user: UserSummary | null;
  last_message: Message | null;
  messages?: Message[];
  created_at: string;
  updated_at: string;
};

export type NotificationType =
  | "claim_submitted"
  | "claim_approved"
  | "claim_rejected";

export type Notification = {
  id: number;
  recipient: UserSummary;
  actor: UserSummary | null;
  notification_type: NotificationType | string;
  notification_type_display: string;
  title: string;
  message: string;
  item: Item | null;
  claim: Claim | null;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
};

export type LoginPayload = {
  username: string;
  password: string;
};

export type RegisterPayload = {
  username: string;
  email: string;
  password: string;
  phone_number: string;
  identification_number: string;
  role: "student" | "staff";
};

export type AuthTokens = {
  access: string;
  refresh: string;
};

export type AuthResult = {
  user: CurrentUser;
  tokens: AuthTokens;
};

export type ClaimPayload = {
  verification_answer?: string;
  proof_details: string;
};

export type ClaimReviewPayload = {
  status: "approved" | "rejected";
  review_note?: string;
};

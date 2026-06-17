import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import {
  IonButton,
  IonContent,
  IonHeader,
  IonIcon,
  IonPage,
  IonSegment,
  IonSegmentButton,
  IonTitle,
  IonToolbar
} from "@ionic/react";
import {
  addCircleOutline,
  arrowBackOutline,
  chatbubbleEllipsesOutline,
  checkmarkCircleOutline,
  closeCircleOutline,
  listOutline,
  logOutOutline,
  notificationsOutline,
  personCircleOutline,
  refreshOutline,
  searchOutline,
  sendOutline
} from "ionicons/icons";

import {
  clearTokens,
  createItem,
  getConversation,
  getCurrentUser,
  getItem,
  getStoredTokens,
  listConversations,
  listItems,
  listNotifications,
  login,
  markAllNotificationsRead,
  markNotificationRead,
  register,
  reviewClaim,
  sendMessage,
  startConversation,
  storeTokens,
  submitClaim
} from "./api";
import type {
  Category,
  Claim,
  Conversation,
  CurrentUser,
  Item,
  ItemStatus,
  Notification,
  RegisterPayload,
  ReportType
} from "./types";

type Screen = "items" | "detail" | "report" | "messages" | "chat" | "notifications" | "claim-review" | "account";
type AuthMode = "login" | "register";

const categories: Array<{ value: Category; label: string }> = [
  { value: "electronics", label: "Electronics" },
  { value: "documents", label: "Documents" },
  { value: "id_cards", label: "ID Cards" },
  { value: "keys", label: "Keys" },
  { value: "books", label: "Books" },
  { value: "clothing", label: "Clothing" },
  { value: "other", label: "Other" }
];

const statuses: Array<{ value: ItemStatus; label: string }> = [
  { value: "lost", label: "Lost" },
  { value: "found", label: "Found" },
  { value: "claimed", label: "Claimed" },
  { value: "returned", label: "Returned" }
];

const today = new Date().toISOString().slice(0, 10);

const initialReportForm = {
  report_type: "lost" as ReportType,
  title: "",
  description: "",
  category: "electronics" as Category,
  location: "",
  event_date: today,
  image: null as File | null,
  verification_question: "",
  verification_answer: ""
};

const initialClaimForm = {
  verification_answer: "",
  proof_details: ""
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric"
  }).format(new Date(value));
}

function shortMessage(message: string, limit = 96) {
  return message.length > limit ? `${message.slice(0, limit - 1)}...` : message;
}

function itemLabel(item: Item) {
  return item.title ?? item.public_label ?? "Found item";
}

function itemPostedLabel(item: Item) {
  return `Posted ${formatDate(item.created_at)}`;
}

export default function App() {
  const [screen, setScreen] = useState<Screen>("items");
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [selectedItem, setSelectedItem] = useState<Item | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [selectedClaim, setSelectedClaim] = useState<Claim | null>(null);
  const [reviewNote, setReviewNote] = useState("");
  const [messageBody, setMessageBody] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [itemsLoading, setItemsLoading] = useState(true);
  const [filters, setFilters] = useState({
    q: "",
    status: "",
    category: "",
    report_type: ""
  });
  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [registerForm, setRegisterForm] = useState<RegisterPayload>({
    username: "",
    email: "",
    password: "",
    phone_number: "",
    identification_number: "",
    role: "student"
  });
  const [reportForm, setReportForm] = useState(initialReportForm);
  const [claimForm, setClaimForm] = useState(initialClaimForm);

  const isOwnItem = useMemo(
    () => Boolean(user && selectedItem?.reported_by?.id === user.id),
    [selectedItem, user]
  );
  const unreadCount = useMemo(
    () => notifications.filter((notification) => !notification.is_read).length,
    [notifications]
  );

  useEffect(() => {
    void loadItems();

    if (getStoredTokens()) {
      void loadUser();
    }
  }, []);

  async function loadUser() {
    try {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
      try {
        const nextNotifications = await listNotifications();
        setNotifications(nextNotifications);
      } catch {
        setNotifications([]);
      }
    } catch {
      clearTokens();
      setUser(null);
      setNotifications([]);
    }
  }

  async function loadItems(nextFilters = filters) {
    setItemsLoading(true);
    try {
      const nextItems = await listItems(nextFilters);
      setItems(nextItems);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not load items.");
    } finally {
      setItemsLoading(false);
    }
  }

  async function openItem(itemId: number) {
    setBusy(true);
    try {
      const item = await getItem(itemId);
      setSelectedItem(item);
      setClaimForm(initialClaimForm);
      setScreen("detail");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not open item.");
    } finally {
      setBusy(false);
    }
  }

  async function openMessages() {
    if (!user) {
      setScreen("account");
      return;
    }

    setScreen("messages");
    setBusy(true);
    try {
      const nextConversations = await listConversations();
      setConversations(nextConversations);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not load messages.");
    } finally {
      setBusy(false);
    }
  }

  async function refreshNotifications() {
    const nextNotifications = await listNotifications();
    setNotifications(nextNotifications);
    return nextNotifications;
  }

  async function openNotifications() {
    if (!user) {
      setScreen("account");
      return;
    }

    setScreen("notifications");
    setBusy(true);
    try {
      await refreshNotifications();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not load notifications.");
    } finally {
      setBusy(false);
    }
  }

  function openClaimReview(claim: Claim) {
    setSelectedClaim(claim);
    setSelectedItem(claim.item);
    setReviewNote(claim.review_note ?? "");
    setScreen("claim-review");
  }

  async function openChat(conversationId: number) {
    setBusy(true);
    try {
      const conversation = await getConversation(conversationId);
      setSelectedConversation(conversation);
      setScreen("chat");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not open chat.");
    } finally {
      setBusy(false);
    }
  }

  function changeScreen(nextScreen: Screen) {
    if (nextScreen === "messages") {
      void openMessages();
      return;
    }

    if (nextScreen === "notifications") {
      void openNotifications();
      return;
    }

    if (nextScreen === "report" && !user) {
      setScreen("account");
      return;
    }

    setScreen(nextScreen);
  }

  async function handleFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await loadItems();
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    try {
      const tokens = await login(loginForm);
      storeTokens(tokens);
      await loadUser();
      setNotice("Signed in.");
      setScreen("items");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not sign in.");
    } finally {
      setBusy(false);
    }
  }

  async function handleRegister(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    try {
      const result = await register(registerForm);
      storeTokens(result.tokens);
      setUser(result.user);
      setNotice("Account created.");
      setScreen("items");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not create account.");
    } finally {
      setBusy(false);
    }
  }

  function handleLogout() {
    clearTokens();
    setUser(null);
    setConversations([]);
    setSelectedConversation(null);
    setNotifications([]);
    setNotice("Signed out.");
    setScreen("items");
  }

  async function handleReport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    try {
      const formData = new FormData();
      formData.set("report_type", reportForm.report_type);
      formData.set("title", reportForm.title);
      formData.set("description", reportForm.description);
      formData.set("category", reportForm.category);
      formData.set("location", reportForm.location);
      formData.set("event_date", reportForm.event_date);
      formData.set("verification_question", reportForm.verification_question);
      formData.set("verification_answer", reportForm.verification_answer);
      if (reportForm.image) {
        formData.set("image", reportForm.image);
      }

      const created = await createItem(formData);
      setReportForm(initialReportForm);
      setSelectedItem(created);
      await loadItems();
      setNotice("Report submitted.");
      setScreen("detail");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not submit report.");
    } finally {
      setBusy(false);
    }
  }

  function handleImage(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setReportForm((current) => ({ ...current, image: file }));
  }

  async function handleStartConversation() {
    if (!selectedItem) {
      return;
    }

    if (!user) {
      setScreen("account");
      return;
    }

    setBusy(true);
    try {
      const conversation = await startConversation(selectedItem.id);
      setSelectedConversation(conversation);
      setScreen("chat");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not start conversation.");
    } finally {
      setBusy(false);
    }
  }

  async function handleSubmitClaim(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedItem) {
      return;
    }

    if (!user) {
      setScreen("account");
      return;
    }

    setBusy(true);
    try {
      await submitClaim(selectedItem.id, {
        verification_answer: claimForm.verification_answer,
        proof_details: claimForm.proof_details
      });
      const refreshedItem = await getItem(selectedItem.id);
      setSelectedItem(refreshedItem);
      setClaimForm(initialClaimForm);
      setNotice("Claim submitted for review.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not submit claim.");
    } finally {
      setBusy(false);
    }
  }

  async function handleSendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedConversation || !messageBody.trim()) {
      return;
    }

    setBusy(true);
    try {
      await sendMessage(selectedConversation.id, messageBody.trim());
      setMessageBody("");
      await openChat(selectedConversation.id);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not send message.");
    } finally {
      setBusy(false);
    }
  }

  async function handleNotification(notification: Notification) {
    setBusy(true);
    try {
      let nextNotification = notification;
      if (!notification.is_read) {
        nextNotification = await markNotificationRead(notification.id);
        setNotifications((current) =>
          current.map((item) =>
            item.id === nextNotification.id ? nextNotification : item
          )
        );
      }

      if (nextNotification.notification_type === "claim_submitted" && nextNotification.claim) {
        openClaimReview(nextNotification.claim);
        return;
      }

      const itemId = nextNotification.item?.id ?? nextNotification.claim?.item?.id;
      if (itemId) {
        const item = await getItem(itemId);
        setSelectedItem(item);
        setClaimForm(initialClaimForm);
        setScreen("detail");
      }
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not open notification.");
    } finally {
      setBusy(false);
    }
  }

  async function handleReviewClaim(nextStatus: "approved" | "rejected") {
    if (!selectedClaim) {
      return;
    }

    setBusy(true);
    try {
      const reviewedClaim = await reviewClaim(selectedClaim.id, {
        status: nextStatus,
        review_note: reviewNote.trim()
      });
      setSelectedClaim(reviewedClaim);
      setSelectedItem(reviewedClaim.item);
      await refreshNotifications();
      await loadItems();
      setNotice(nextStatus === "approved" ? "Claim approved." : "Claim rejected.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not review claim.");
    } finally {
      setBusy(false);
    }
  }

  async function handleMarkAllNotificationsRead() {
    setBusy(true);
    try {
      await markAllNotificationsRead();
      await refreshNotifications();
      setNotice("Notifications marked as read.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not update notifications.");
    } finally {
      setBusy(false);
    }
  }

  function renderItems() {
    return (
      <section className="screen stack">
        <form className="filter-panel" onSubmit={handleFilters}>
          <label className="search-field">
            <IonIcon icon={searchOutline} aria-hidden="true" />
            <input
              value={filters.q}
              placeholder={user?.is_staff ? "Search title, description, or location" : "Found items"}
              onChange={(event) => setFilters({ ...filters, q: event.target.value })}
              disabled={!user?.is_staff}
            />
          </label>

          {user?.is_staff && (
            <div className="filter-grid">
              <select
                value={filters.report_type}
                onChange={(event) => setFilters({ ...filters, report_type: event.target.value })}
              >
                <option value="">All reports</option>
                <option value="lost">Lost</option>
                <option value="found">Found</option>
              </select>
              <select
                value={filters.status}
                onChange={(event) => setFilters({ ...filters, status: event.target.value })}
              >
                <option value="">All statuses</option>
                {statuses.map((status) => (
                  <option key={status.value} value={status.value}>{status.label}</option>
                ))}
              </select>
              <select
                value={filters.category}
                onChange={(event) => setFilters({ ...filters, category: event.target.value })}
              >
                <option value="">All categories</option>
                {categories.map((category) => (
                  <option key={category.value} value={category.value}>{category.label}</option>
                ))}
              </select>
            </div>
          )}

          <IonButton type="submit" expand="block" disabled={itemsLoading}>
            <IonIcon icon={refreshOutline} slot="start" />
            Refresh Feed
          </IonButton>
        </form>

        <div className="section-head">
          <div>
            <p className="eyebrow">Campus Feed</p>
            <h1>{items.length} active listing{items.length === 1 ? "" : "s"}</h1>
          </div>
          <IonButton size="small" onClick={() => changeScreen("report")}>
            <IonIcon icon={addCircleOutline} slot="start" />
            Report
          </IonButton>
        </div>

        {itemsLoading ? (
          <div className="empty-panel">Loading listings...</div>
        ) : items.length === 0 ? (
          <div className="empty-panel">No items matched the current filters.</div>
        ) : (
          <div className="item-list">
            {items.map((item) => (
              <button className="item-card" key={item.id} onClick={() => void openItem(item.id)}>
                <div className="item-thumb">
                  {item.image_url ? (
                    <img src={item.image_url} alt={itemLabel(item)} />
                  ) : (
                    <span>{item.can_view_private_details && item.category ? item.category.replace("_", " ") : "Found item"}</span>
                  )}
                  <span className={`pill pill--${item.report_type}`}>
                    {item.report_type_display}
                  </span>
                </div>
                <div className="item-card__body">
                  {item.can_view_private_details ? (
                    <>
                      <div>
                        <h2>{item.title}</h2>
                        <p>{item.location}</p>
                      </div>
                      <div className="item-card__meta">
                        {item.event_date && <span>{formatDate(item.event_date)}</span>}
                        <span>{item.status_display}</span>
                      </div>
                    </>
                  ) : (
                    <>
                      <div>
                        <h2>{itemLabel(item)}</h2>
                        <p>{itemPostedLabel(item)}</p>
                      </div>
                    </>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
      </section>
    );
  }

  function renderDetail() {
    if (!selectedItem) {
      return renderItems();
    }

    const canViewPrivateDetails = Boolean(selectedItem.can_view_private_details);

    return (
      <section className="screen stack">
        <IonButton fill="clear" className="back-button" onClick={() => setScreen("items")}>
          <IonIcon icon={arrowBackOutline} slot="start" />
          Listings
        </IonButton>

        <article className="detail-card">
          <div className="detail-image">
            {selectedItem.image_url ? (
              <img src={selectedItem.image_url} alt={itemLabel(selectedItem)} />
            ) : (
              <span>
                {canViewPrivateDetails
                  ? selectedItem.category_display ?? selectedItem.category
                  : "Found item"}
              </span>
            )}
            <span className={`pill pill--${selectedItem.report_type}`}>
              {selectedItem.report_type_display}
            </span>
          </div>

          <div className="detail-body">
            <div className="detail-title-row">
              <div>
                <h1>{itemLabel(selectedItem)}</h1>
                <p>
                  {canViewPrivateDetails
                    ? selectedItem.location
                    : itemPostedLabel(selectedItem)}
                </p>
              </div>
              {canViewPrivateDetails && (
                <span className="status-chip">{selectedItem.status_display}</span>
              )}
            </div>

            {canViewPrivateDetails && (
              <>
                <dl className="spec-grid">
                  <div>
                    <dt>Category</dt>
                    <dd>{selectedItem.category_display ?? selectedItem.category}</dd>
                  </div>
                  <div>
                    <dt>Date</dt>
                    <dd>{selectedItem.event_date ? formatDate(selectedItem.event_date) : "Not set"}</dd>
                  </div>
                  <div>
                    <dt>Reporter</dt>
                    <dd>{selectedItem.reported_by?.username ?? "Campus user"}</dd>
                  </div>
                  <div>
                    <dt>Posted</dt>
                    <dd>{formatDate(selectedItem.created_at)}</dd>
                  </div>
                </dl>

                <p className="description">{selectedItem.description}</p>
              </>
            )}

            {isOwnItem ? (
              <div className="info-panel">This is your report. Messages about it appear in Messages.</div>
            ) : selectedItem.my_claim ? (
              <div className="info-panel">
                Claim status: {selectedItem.my_claim.status_display}
                {selectedItem.my_claim.answer_matches ? " - verification answer matched" : ""}
                {selectedItem.my_claim.review_note ? ` - ${selectedItem.my_claim.review_note}` : ""}
              </div>
            ) : selectedItem.report_type === "found" && !canViewPrivateDetails ? (
              <form className="claim-panel" onSubmit={handleSubmitClaim}>
                {selectedItem.verification_question && (
                  <label>
                    {selectedItem.verification_question}
                    <input
                      type="password"
                      value={claimForm.verification_answer}
                      onChange={(event) => setClaimForm({ ...claimForm, verification_answer: event.target.value })}
                    />
                  </label>
                )}
                <label>
                  Ownership proof
                  <textarea
                    required
                    rows={4}
                    value={claimForm.proof_details}
                    placeholder="Describe details only the owner would know."
                    onChange={(event) => setClaimForm({ ...claimForm, proof_details: event.target.value })}
                  />
                </label>
                <IonButton type="submit" expand="block" disabled={busy}>
                  Submit Claim
                </IonButton>
              </form>
            ) : canViewPrivateDetails ? (
              <IonButton expand="block" disabled={busy} onClick={() => void handleStartConversation()}>
                <IonIcon icon={chatbubbleEllipsesOutline} slot="start" />
                Message Reporter
              </IonButton>
            ) : (
              <div className="info-panel">Submit a claim so the reporter or staff can review ownership.</div>
            )}
          </div>
        </article>
      </section>
    );
  }

  function renderReport() {
    if (!user) {
      return renderAccount();
    }

    return (
      <section className="screen stack">
        <div className="section-head">
          <div>
            <p className="eyebrow">New Report</p>
            <h1>Submit an item</h1>
          </div>
        </div>

        <form className="form-card" onSubmit={handleReport}>
          <div className="segmented-field">
            <button
              type="button"
              className={reportForm.report_type === "lost" ? "active" : ""}
              onClick={() => setReportForm({ ...reportForm, report_type: "lost" })}
            >
              Lost
            </button>
            <button
              type="button"
              className={reportForm.report_type === "found" ? "active" : ""}
              onClick={() => setReportForm({ ...reportForm, report_type: "found" })}
            >
              Found
            </button>
          </div>

          <label>
            Title
            <input
              required
              value={reportForm.title}
              onChange={(event) => setReportForm({ ...reportForm, title: event.target.value })}
            />
          </label>

          <label>
            Description
            <textarea
              required
              rows={4}
              value={reportForm.description}
              onChange={(event) => setReportForm({ ...reportForm, description: event.target.value })}
            />
          </label>

          <div className="two-column">
            <label>
              Category
              <select
                value={reportForm.category}
                onChange={(event) => setReportForm({ ...reportForm, category: event.target.value as Category })}
              >
                {categories.map((category) => (
                  <option key={category.value} value={category.value}>{category.label}</option>
                ))}
              </select>
            </label>
            <label>
              Date
              <input
                required
                type="date"
                value={reportForm.event_date}
                onChange={(event) => setReportForm({ ...reportForm, event_date: event.target.value })}
              />
            </label>
          </div>

          <label>
            Location
            <input
              required
              value={reportForm.location}
              onChange={(event) => setReportForm({ ...reportForm, location: event.target.value })}
            />
          </label>

          <label>
            Photo
            <input accept="image/*" capture="environment" type="file" onChange={handleImage} />
          </label>

          {reportForm.image && <p className="file-note">{reportForm.image.name}</p>}

          {reportForm.report_type === "found" && (
            <>
              <label>
                Verification Question
                <input
                  value={reportForm.verification_question}
                  placeholder="What detail should the owner know?"
                  onChange={(event) => setReportForm({ ...reportForm, verification_question: event.target.value })}
                />
              </label>
              <label>
                Private Answer
                <input
                  type="password"
                  value={reportForm.verification_answer}
                  placeholder="Hidden answer for reviewers"
                  onChange={(event) => setReportForm({ ...reportForm, verification_answer: event.target.value })}
                />
              </label>
            </>
          )}

          <IonButton type="submit" expand="block" disabled={busy}>
            <IonIcon icon={addCircleOutline} slot="start" />
            Submit Report
          </IonButton>
        </form>
      </section>
    );
  }

  function renderMessages() {
    if (!user) {
      return renderAccount();
    }

    return (
      <section className="screen stack">
        <div className="section-head">
          <div>
            <p className="eyebrow">Messages</p>
            <h1>{conversations.length} conversation{conversations.length === 1 ? "" : "s"}</h1>
          </div>
          <IonButton size="small" onClick={() => void openMessages()} disabled={busy}>
            <IonIcon icon={refreshOutline} slot="start" />
            Refresh
          </IonButton>
        </div>

        {conversations.length === 0 ? (
          <div className="empty-panel">No conversations yet.</div>
        ) : (
          <div className="conversation-list">
            {conversations.map((conversation) => (
              <button
                className="conversation-card"
                key={conversation.id}
                onClick={() => void openChat(conversation.id)}
              >
                <div className="avatar">{conversation.other_user?.username.slice(0, 1).toUpperCase() ?? "C"}</div>
                <div>
                  <h2>{itemLabel(conversation.item)}</h2>
                  <p>{conversation.other_user?.username ?? "Campus user"}</p>
                  <span>
                    {conversation.last_message
                      ? shortMessage(conversation.last_message.body)
                      : "No messages yet."}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </section>
    );
  }

  function renderNotifications() {
    if (!user) {
      return renderAccount();
    }

    return (
      <section className="screen stack">
        <div className="section-head">
          <div>
            <p className="eyebrow">Alerts</p>
            <h1>{unreadCount} unread notification{unreadCount === 1 ? "" : "s"}</h1>
          </div>
          <div className="section-actions">
            <IonButton size="small" fill="outline" onClick={() => void handleMarkAllNotificationsRead()} disabled={busy || unreadCount === 0}>
              Mark Read
            </IonButton>
            <IonButton size="small" onClick={() => void openNotifications()} disabled={busy}>
              <IonIcon icon={refreshOutline} slot="start" />
              Refresh
            </IonButton>
          </div>
        </div>

        {notifications.length === 0 ? (
          <div className="empty-panel">No notifications yet.</div>
        ) : (
          <div className="notification-list">
            {notifications.map((notification) => (
              <button
                className={`notification-card ${notification.is_read ? "" : "notification-card--unread"}`}
                key={notification.id}
                onClick={() => void handleNotification(notification)}
              >
                <span className="notification-dot" aria-hidden="true" />
                <div>
                  <div className="notification-card__head">
                    <h2>{notification.title}</h2>
                    <span>{formatDate(notification.created_at)}</span>
                  </div>
                  <p>{notification.message}</p>
                  <span className="notification-meta">
                    {notification.actor?.username ? `${notification.actor.username} - ` : ""}
                    {notification.notification_type_display}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </section>
    );
  }

  function renderClaimReview() {
    if (!selectedClaim) {
      return renderNotifications();
    }

    const claim = selectedClaim;
    const claimItem = claim.item;
    const canReview = claim.status === "pending";

    return (
      <section className="screen stack">
        <IonButton fill="clear" className="back-button" onClick={() => setScreen("notifications")}>
          <IonIcon icon={arrowBackOutline} slot="start" />
          Alerts
        </IonButton>

        <article className="detail-card">
          <div className="detail-image">
            {claimItem.image_url ? (
              <img src={claimItem.image_url} alt={itemLabel(claimItem)} />
            ) : (
              <span>{claimItem.category_display ?? claimItem.category ?? "Found item"}</span>
            )}
            <span className={`pill pill--${claimItem.report_type}`}>
              {claimItem.report_type_display}
            </span>
          </div>

          <div className="detail-body">
            <div className="detail-title-row">
              <div>
                <p className="eyebrow">Claim Review</p>
                <h1>{itemLabel(claimItem)}</h1>
                <p>{claimItem.location ?? itemPostedLabel(claimItem)}</p>
              </div>
              <span className="status-chip">{claim.status_display}</span>
            </div>

            <dl className="spec-grid">
              <div>
                <dt>Claimant</dt>
                <dd>{claim.claimant.username}</dd>
              </div>
              <div>
                <dt>ID Number</dt>
                <dd>{claim.claimant_profile?.identification_number ?? "Not set"}</dd>
              </div>
              <div>
                <dt>Answer</dt>
                <dd>{claim.answer_matches ? "Matched" : "No match"}</dd>
              </div>
              <div>
                <dt>Submitted</dt>
                <dd>{formatDate(claim.created_at)}</dd>
              </div>
            </dl>

            <div className="proof-panel">
              <p className="eyebrow">Ownership Proof</p>
              <p>{claim.proof_details}</p>
            </div>

            {canReview ? (
              <div className="claim-review-panel">
                <label>
                  Review note
                  <textarea
                    rows={3}
                    value={reviewNote}
                    placeholder="Optional note for the claimant"
                    onChange={(event) => setReviewNote(event.target.value)}
                  />
                </label>
                <div className="review-actions">
                  <IonButton color="danger" fill="outline" disabled={busy} onClick={() => void handleReviewClaim("rejected")}>
                    <IonIcon icon={closeCircleOutline} slot="start" />
                    Reject
                  </IonButton>
                  <IonButton color="secondary" disabled={busy} onClick={() => void handleReviewClaim("approved")}>
                    <IonIcon icon={checkmarkCircleOutline} slot="start" />
                    Approve
                  </IonButton>
                </div>
              </div>
            ) : (
              <div className="info-panel">
                Claim status: {claim.status_display}
                {claim.review_note ? ` - ${claim.review_note}` : ""}
              </div>
            )}
          </div>
        </article>
      </section>
    );
  }

  function renderChat() {
    if (!selectedConversation) {
      return renderMessages();
    }

    return (
      <section className="screen chat-screen">
        <IonButton fill="clear" className="back-button" onClick={() => void openMessages()}>
          <IonIcon icon={arrowBackOutline} slot="start" />
          Messages
        </IonButton>

        <div className="chat-head">
          <div>
            <p className="eyebrow">{selectedConversation.other_user?.username ?? "Conversation"}</p>
            <h1>{itemLabel(selectedConversation.item)}</h1>
          </div>
          <span className={`pill pill--${selectedConversation.item.report_type}`}>
            {selectedConversation.item.report_type_display}
          </span>
        </div>

        <div className="message-list">
          {(selectedConversation.messages ?? []).length === 0 ? (
            <div className="empty-panel">Start the conversation with a short message.</div>
          ) : (
            selectedConversation.messages?.map((message) => (
              <div
                className={`message-bubble ${message.is_mine ? "message-bubble--mine" : ""}`}
                key={message.id}
              >
                <p>{message.body}</p>
                <span>{message.sender.username} · {formatDate(message.created_at)}</span>
              </div>
            ))
          )}
        </div>

        <form className="composer" onSubmit={handleSendMessage}>
          <input
            value={messageBody}
            placeholder="Write a message"
            onChange={(event) => setMessageBody(event.target.value)}
          />
          <IonButton type="submit" disabled={busy || !messageBody.trim()}>
            <IonIcon icon={sendOutline} slot="icon-only" aria-label="Send" />
          </IonButton>
        </form>
      </section>
    );
  }

  function renderAccount() {
    return (
      <section className="screen stack">
        {user ? (
          <div className="form-card">
            <div className="account-head">
              <div className="avatar avatar--large">{user.username.slice(0, 1).toUpperCase()}</div>
              <div>
                <p className="eyebrow">Signed In</p>
                <h1>{user.username}</h1>
                <p>{user.email || "No email added"}</p>
              </div>
            </div>

            <dl className="spec-grid">
              <div>
                <dt>Role</dt>
                <dd>{user.profile?.role ?? "student"}</dd>
              </div>
              <div>
                <dt>ID Number</dt>
                <dd>{user.profile?.identification_number ?? "Not set"}</dd>
              </div>
              <div>
                <dt>Phone</dt>
                <dd>{user.profile?.phone_number || "Not set"}</dd>
              </div>
              <div>
                <dt>Access</dt>
                <dd>{user.is_staff ? "Staff" : "Student"}</dd>
              </div>
            </dl>

            <IonButton color="danger" expand="block" onClick={handleLogout}>
              <IonIcon icon={logOutOutline} slot="start" />
              Sign Out
            </IonButton>
          </div>
        ) : (
          <div className="form-card">
            <IonSegment
              value={authMode}
              onIonChange={(event) => setAuthMode(event.detail.value as AuthMode)}
            >
              <IonSegmentButton value="login">Login</IonSegmentButton>
              <IonSegmentButton value="register">Sign Up</IonSegmentButton>
            </IonSegment>

            {authMode === "login" ? (
              <form className="auth-form" onSubmit={handleLogin}>
                <label>
                  Username
                  <input
                    required
                    autoComplete="username"
                    value={loginForm.username}
                    onChange={(event) => setLoginForm({ ...loginForm, username: event.target.value })}
                  />
                </label>
                <label>
                  Password
                  <input
                    required
                    type="password"
                    autoComplete="current-password"
                    value={loginForm.password}
                    onChange={(event) => setLoginForm({ ...loginForm, password: event.target.value })}
                  />
                </label>
                <IonButton type="submit" expand="block" disabled={busy}>
                  <IonIcon icon={personCircleOutline} slot="start" />
                  Login
                </IonButton>
              </form>
            ) : (
              <form className="auth-form" onSubmit={handleRegister}>
                <label>
                  Username
                  <input
                    required
                    autoComplete="username"
                    value={registerForm.username}
                    onChange={(event) => setRegisterForm({ ...registerForm, username: event.target.value })}
                  />
                </label>
                <label>
                  Email
                  <input
                    type="email"
                    autoComplete="email"
                    value={registerForm.email}
                    onChange={(event) => setRegisterForm({ ...registerForm, email: event.target.value })}
                  />
                </label>
                <label>
                  Phone
                  <input
                    autoComplete="tel"
                    value={registerForm.phone_number}
                    onChange={(event) => setRegisterForm({ ...registerForm, phone_number: event.target.value })}
                  />
                </label>
                <label>
                  Identification Number
                  <input
                    required
                    value={registerForm.identification_number}
                    onChange={(event) => setRegisterForm({ ...registerForm, identification_number: event.target.value })}
                  />
                </label>
                <label>
                  Role
                  <select
                    value={registerForm.role}
                    onChange={(event) => setRegisterForm({ ...registerForm, role: event.target.value as "student" | "staff" })}
                  >
                    <option value="student">Student</option>
                    <option value="staff">Staff</option>
                  </select>
                </label>
                <label>
                  Password
                  <input
                    required
                    minLength={8}
                    type="password"
                    autoComplete="new-password"
                    value={registerForm.password}
                    onChange={(event) => setRegisterForm({ ...registerForm, password: event.target.value })}
                  />
                </label>
                <IonButton type="submit" expand="block" disabled={busy}>
                  <IonIcon icon={personCircleOutline} slot="start" />
                  Create Account
                </IonButton>
              </form>
            )}
          </div>
        )}
      </section>
    );
  }

  return (
    <IonPage>
      <IonHeader>
        <IonToolbar>
          <IonTitle>Digital Lost & Found</IonTitle>
        </IonToolbar>
      </IonHeader>

      <IonContent>
        <main className="page-body">
          {notice && (
            <button className="notice" onClick={() => setNotice("")}>
              {notice}
            </button>
          )}

          {screen === "items" && renderItems()}
          {screen === "detail" && renderDetail()}
          {screen === "report" && renderReport()}
          {screen === "messages" && renderMessages()}
          {screen === "chat" && renderChat()}
          {screen === "notifications" && renderNotifications()}
          {screen === "claim-review" && renderClaimReview()}
          {screen === "account" && renderAccount()}
        </main>
      </IonContent>

      <nav className="app-tabs" aria-label="Primary">
        <button className={screen === "items" || screen === "detail" ? "active" : ""} onClick={() => changeScreen("items")}>
          <IonIcon icon={listOutline} aria-hidden="true" />
          <span>Items</span>
        </button>
        <button className={screen === "report" ? "active" : ""} onClick={() => changeScreen("report")}>
          <IonIcon icon={addCircleOutline} aria-hidden="true" />
          <span>Report</span>
        </button>
        <button className={screen === "messages" || screen === "chat" ? "active" : ""} onClick={() => changeScreen("messages")}>
          <IonIcon icon={chatbubbleEllipsesOutline} aria-hidden="true" />
          <span>Messages</span>
        </button>
        <button className={screen === "notifications" || screen === "claim-review" ? "active" : ""} onClick={() => changeScreen("notifications")}>
          <span className="tab-icon-wrap">
            <IonIcon icon={notificationsOutline} aria-hidden="true" />
            {unreadCount > 0 && (
              <span className="tab-badge">{unreadCount > 9 ? "9+" : unreadCount}</span>
            )}
          </span>
          <span>Alerts</span>
        </button>
        <button className={screen === "account" ? "active" : ""} onClick={() => changeScreen("account")}>
          <IonIcon icon={personCircleOutline} aria-hidden="true" />
          <span>Account</span>
        </button>
      </nav>
    </IonPage>
  );
}

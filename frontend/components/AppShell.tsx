"use client";

import { AlertTriangle, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { ArtifactPanel } from "@/components/artifact/ArtifactPanel";
import { ChatHeader } from "@/components/chat/ChatHeader";
import { Composer } from "@/components/chat/Composer";
import { EmptyState } from "@/components/chat/EmptyState";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { TypingIndicator } from "@/components/ui/Skeleton";
import { ApiError, api } from "@/lib/api-client";
import { ArtifactOut, MessageOut, SessionOut } from "@/types";

interface ArtifactPanelState {
  open: boolean;
  artifact: ArtifactOut | null;
  loading: boolean;
  error: string | null;
  fullscreen: boolean;
  regenerate: (() => void) | null;
}

const INITIAL_PANEL: ArtifactPanelState = {
  open: false,
  artifact: null,
  loading: false,
  error: null,
  fullscreen: false,
  regenerate: null,
};

export function AppShell() {
  const [sessions, setSessions] = useState<SessionOut[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageOut[]>([]);
  const [artifactsByMessage, setArtifactsByMessage] = useState<Record<string, ArtifactOut>>({});
  const [sending, setSending] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const [panel, setPanel] = useState<ArtifactPanelState>(INITIAL_PANEL);

  useEffect(() => {
    refreshSessions();
  }, []);

  async function refreshSessions() {
    try {
      const data = await api.listSessions();
      setSessions(data);
    } catch {
      setGlobalError(
        "Can't reach the backend API. Make sure it's running (see README Quick Start) and refresh."
      );
    }
  }

  async function openSession(id: string) {
    setActiveSessionId(id);
    setMobileSidebarOpen(false);
    setPanel(INITIAL_PANEL);
    try {
      const [msgs, artifacts] = await Promise.all([api.listMessages(id), api.listSessionArtifacts(id)]);
      setMessages(msgs);
      const map: Record<string, ArtifactOut> = {};
      for (const a of artifacts) if (a.message_id) map[a.message_id] = a;
      setArtifactsByMessage(map);
    } catch (e) {
      setGlobalError(e instanceof ApiError ? e.message : "Failed to load conversation.");
    }
  }

  function startNewChat() {
    setActiveSessionId(null);
    setMessages([]);
    setArtifactsByMessage({});
    setPanel(INITIAL_PANEL);
    setMobileSidebarOpen(false);
  }

  async function deleteSession(id: string) {
    try {
      await api.deleteSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (id === activeSessionId) startNewChat();
    } catch (e) {
      setGlobalError(e instanceof ApiError ? e.message : "Failed to delete conversation.");
    }
  }

  async function ensureSession(): Promise<string> {
    if (activeSessionId) return activeSessionId;
    const session = await api.createSession();
    setSessions((prev) => [session, ...prev]);
    setActiveSessionId(session.id);
    return session.id;
  }

  async function handleSend(text: string) {
    setGlobalError(null);
    setSending(true);
    const optimisticUser: MessageOut = {
      id: `optimistic-${Date.now()}`,
      role: "user",
      content: text,
      model: null,
      provider: null,
      sources: [],
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticUser]);

    try {
      const sessionId = await ensureSession();
      const result = await api.sendMessage(sessionId, text);

      setMessages((prev) => [
        ...prev.filter((m) => m.id !== optimisticUser.id),
        result.user_message,
        result.assistant_message,
      ]);

      if (result.artifact) {
        setArtifactsByMessage((prev) => ({ ...prev, [result.assistant_message.id]: result.artifact! }));
        setPanel({
          open: true,
          artifact: result.artifact,
          loading: false,
          error: null,
          fullscreen: false,
          regenerate: () => regenerateArtifact(sessionId, text, result.artifact!.type),
        });
      }

      refreshSessions();
    } catch (e) {
      setMessages((prev) => prev.filter((m) => m.id !== optimisticUser.id));
      setGlobalError(
        e instanceof ApiError ? `${e.message}` : "Something went wrong sending your message. Please try again."
      );
    } finally {
      setSending(false);
    }
  }

  async function regenerateArtifact(sessionId: string, request: string, type: "markdown" | "html") {
    setPanel((p) => ({ ...p, loading: true, error: null }));
    try {
      const artifact = await api.createArtifact(sessionId, request, type);
      setPanel((p) => ({ ...p, loading: false, artifact }));
    } catch (e) {
      setPanel((p) => ({
        ...p,
        loading: false,
        error: e instanceof ApiError ? e.message : "Failed to regenerate artifact.",
      }));
    }
  }

  function openArtifact(artifact: ArtifactOut) {
    setPanel({
      open: true,
      artifact,
      loading: false,
      error: null,
      fullscreen: false,
      regenerate: activeSessionId
        ? () => regenerateArtifact(activeSessionId, `Regenerate: ${artifact.title}`, artifact.type)
        : null,
    });
  }

  const activeTitle = useMemo(
    () => sessions.find((s) => s.id === activeSessionId)?.title || "New chat",
    [sessions, activeSessionId]
  );

  return (
    <div className="flex h-dvh w-full overflow-hidden bg-canvas">
      <div className="hidden lg:block">
        <Sidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelect={openSession}
          onNewChat={startNewChat}
          onDelete={deleteSession}
        />
      </div>

      {mobileSidebarOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setMobileSidebarOpen(false)} />
          <div className="relative animate-slide-in">
            <Sidebar
              sessions={sessions}
              activeSessionId={activeSessionId}
              onSelect={openSession}
              onNewChat={startNewChat}
              onDelete={deleteSession}
              onCloseMobile={() => setMobileSidebarOpen(false)}
            />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1">
        <div className="flex min-w-0 flex-1 flex-col">
          <ChatHeader
            title={activeTitle}
            onOpenSidebar={() => setMobileSidebarOpen(true)}
            onToggleArtifactPanel={() => setPanel((p) => ({ ...p, open: !p.open }))}
            artifactPanelAvailable={!!panel.artifact}
          />

          {globalError && (
            <div className="flex items-center justify-between gap-2 border-b border-danger/20 bg-danger/5 px-4 py-2 text-xs text-danger">
              <span className="inline-flex items-center gap-1.5">
                <AlertTriangle size={13} /> {globalError}
              </span>
              <button onClick={() => setGlobalError(null)} aria-label="Dismiss error">
                <X size={13} />
              </button>
            </div>
          )}

          <div className="flex-1 overflow-y-auto">
            {messages.length === 0 ? (
              <EmptyState onPick={handleSend} />
            ) : (
              <div className="mx-auto max-w-3xl space-y-4 px-4 py-6">
                {messages.map((m) => (
                  <MessageBubble
                    key={m.id}
                    message={m}
                    artifact={artifactsByMessage[m.id]}
                    onOpenArtifact={openArtifact}
                  />
                ))}
                {sending && (
                  <div className="flex justify-start">
                    <div className="rounded-2xl rounded-tl-sm border border-border bg-surface px-4">
                      <TypingIndicator />
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <Composer onSend={handleSend} disabled={sending} />
        </div>

        {panel.open && (
          <ArtifactPanel
            artifact={panel.artifact}
            loading={panel.loading}
            error={panel.error}
            onClose={() => setPanel(INITIAL_PANEL)}
            onRegenerate={panel.regenerate || undefined}
            fullscreen={panel.fullscreen}
            onToggleFullscreen={() => setPanel((p) => ({ ...p, fullscreen: !p.fullscreen }))}
          />
        )}
      </div>
    </div>
  );
}

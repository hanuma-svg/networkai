"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { getSupabase, ActionQueueItem } from "@/lib/supabase";
import {
  Sparkles,
  ExternalLink,
  Copy,
  Check,
  X,
  RefreshCw,
  Search,
  PenSquare,
  Download,
  AlertTriangle,
  Send,
  UserCheck,
  MessageSquare,
  UserPlus,
  Wifi,
  WifiOff,
} from "lucide-react";

export default function MobileDashboard() {
  const [queue, setQueue] = useState<ActionQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [online, setOnline] = useState(true);
  const [realtimeConnected, setRealtimeConnected] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Modals & Install Prompt
  const [showDiscoverModal, setShowDiscoverModal] = useState(false);
  const [discoverTopic, setDiscoverTopic] = useState("agentic-ai");
  const [discovering, setDiscovering] = useState(false);

  const [showPostModal, setShowPostModal] = useState(false);
  const [postContent, setPostContent] = useState("");
  const [publishing, setPublishing] = useState(false);

  const [installPrompt, setInstallPrompt] = useState<any>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Show temporary toast
  const triggerToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  // 1. Fetch queue from API + fallback to local storage
  const fetchQueue = useCallback(async () => {
    try {
      setRefreshing(true);
      const res = await fetch(`${apiUrl}/api/queue?status=pending_approval`);
      if (res.ok) {
        const data: ActionQueueItem[] = await res.json();
        setQueue(data);
        localStorage.setItem("networkai_cached_queue", JSON.stringify(data));
      } else {
        throw new Error("API returned non-200");
      }
    } catch (err) {
      console.warn("Using offline cached queue:", err);
      const cached = localStorage.getItem("networkai_cached_queue");
      if (cached) {
        try {
          setQueue(JSON.parse(cached));
        } catch (_) {}
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [apiUrl]);

  // 2. Offline / Online event listeners
  useEffect(() => {
    setOnline(navigator.onLine);
    const handleOnline = () => {
      setOnline(true);
      fetchQueue();
    };
    const handleOffline = () => setOnline(false);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    // Capture beforeinstallprompt for PWA installation
    const handleInstallPrompt = (e: Event) => {
      e.preventDefault();
      setInstallPrompt(e);
    };
    window.addEventListener("beforeinstallprompt", handleInstallPrompt);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
      window.removeEventListener("beforeinstallprompt", handleInstallPrompt);
    };
  }, [fetchQueue]);

  // 3. Initial load & Supabase Realtime Subscription
  useEffect(() => {
    fetchQueue();

    try {
      const supabase = getSupabase();
      const channel = supabase
        .channel("realtime-action-queue")
        .on(
          "postgres_changes",
          { event: "*", schema: "public", table: "action_queue" },
          (payload) => {
            console.log("[Supabase Realtime] action_queue change:", payload);
            if (payload.eventType === "INSERT") {
              const newItem = payload.new as ActionQueueItem;
              if (newItem.status === "pending_approval") {
                setQueue((prev) => [newItem, ...prev.filter((i) => i.id !== newItem.id)]);
                triggerToast("⚡ New AI draft received in real-time!");
              }
            } else if (payload.eventType === "UPDATE") {
              const updatedItem = payload.new as ActionQueueItem;
              if (updatedItem.status !== "pending_approval") {
                setQueue((prev) => prev.filter((i) => i.id !== updatedItem.id));
              } else {
                setQueue((prev) =>
                  prev.map((i) => (i.id === updatedItem.id ? { ...i, ...updatedItem } : i))
                );
              }
            } else if (payload.eventType === "DELETE") {
              setQueue((prev) => prev.filter((i) => i.id !== payload.old.id));
            }
          }
        )
        .subscribe((status) => {
          if (status === "SUBSCRIBED") {
            setRealtimeConnected(true);
          } else {
            setRealtimeConnected(false);
          }
        });

      return () => {
        supabase.removeChannel(channel);
      };
    } catch (err) {
      console.warn("Supabase Realtime subscription error:", err);
    }
  }, [fetchQueue]);

  // 4. Update draft text locally in card
  const handleDraftChange = (id: string, text: string) => {
    setQueue((prev) =>
      prev.map((item) => (item.id === id ? { ...item, content: text } : item))
    );
  };

  // 5. 1-Tap "Copy & Open LinkedIn"
  const handleCopyAndOpen = async (item: ActionQueueItem) => {
    try {
      // Copy to clipboard
      await navigator.clipboard.writeText(item.content);
      setCopiedId(item.id);
      setTimeout(() => setCopiedId(null), 2500);

      // Trigger approval endpoint
      fetch(`${apiUrl}/api/queue/${item.id}/approve`, {
        method: "POST",
      }).catch((err) => console.warn("Approve background error:", err));

      // Remove from pending queue locally
      setQueue((prev) => prev.filter((i) => i.id !== item.id));

      // Derive LinkedIn target URL
      let targetUrl = item.metadata?.target_url || item.contact?.linkedin_url || "https://www.linkedin.com";
      if (!targetUrl.startsWith("http")) {
        targetUrl = `https://www.linkedin.com/search/results/all/?keywords=${encodeURIComponent(
          item.contact?.full_name || ""
        )}`;
      }

      triggerToast("Copied draft! Opening LinkedIn...");
      window.open(targetUrl, "_blank");
    } catch (err) {
      console.error("Copy failed:", err);
      triggerToast("Clipboard copy failed");
    }
  };

  // 6. Dismiss Action
  const handleDismiss = (id: string) => {
    setQueue((prev) => prev.filter((i) => i.id !== id));
    triggerToast("Draft dismissed");
  };

  // 7. Discover Builders
  const handleDiscover = async () => {
    setDiscovering(true);
    try {
      const res = await fetch(`${apiUrl}/api/discover`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: discoverTopic, limit: 5 }),
      });
      if (res.ok) {
        const data = await res.json();
        triggerToast(`Discovered ${data.builders_found} builders! Drafts added.`);
        fetchQueue();
        setShowDiscoverModal(false);
      } else {
        triggerToast("Failed to run discovery");
      }
    } catch (err) {
      triggerToast("Error connecting to discovery service");
    } finally {
      setDiscovering(false);
    }
  };

  // 8. Publish Post
  const handlePublishPost = async () => {
    if (!postContent.trim()) return;
    setPublishing(true);
    try {
      const res = await fetch(`${apiUrl}/api/publish-post`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ commentary: postContent }),
      });
      if (res.ok) {
        triggerToast("Post published to LinkedIn feed!");
        setPostContent("");
        setShowPostModal(false);
      } else {
        triggerToast("Publishing returned error");
      }
    } catch (err) {
      triggerToast("Network error publishing post");
    } finally {
      setPublishing(false);
    }
  };

  // 9. Install PWA
  const handleInstallClick = () => {
    if (installPrompt) {
      installPrompt.prompt();
      installPrompt.userChoice.then(() => setInstallPrompt(null));
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-slate-950 text-slate-100 max-w-md mx-auto relative pb-28">
      {/* Top Mobile Bar */}
      <header className="sticky top-0 z-30 bg-slate-950/80 backdrop-blur-md border-b border-slate-800/80 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight leading-none text-white">NetworkAI</h1>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className={`inline-block h-2 w-2 rounded-full ${online ? "bg-emerald-400" : "bg-rose-400"}`} />
              <span className="text-[11px] font-medium text-slate-400">
                {realtimeConnected ? "Realtime Cloud Sync" : online ? "Connected" : "Offline Cache"}
              </span>
            </div>
          </div>
        </div>

        <button
          onClick={fetchQueue}
          disabled={refreshing}
          className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 active:scale-95 transition"
          aria-label="Refresh queue"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin text-indigo-400" : ""}`} />
        </button>
      </header>

      {/* Floating Toast Notification */}
      {toastMessage && (
        <div className="fixed top-16 left-1/2 -translate-x-1/2 z-50 bg-indigo-600 text-white text-xs font-semibold px-4 py-2 rounded-full shadow-2xl shadow-indigo-900/50 animate-bounce">
          {toastMessage}
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1 px-4 py-4 space-y-4">
        {/* Queue Header */}
        <div className="flex items-center justify-between px-1">
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Action Queue</span>
            <h2 className="text-lg font-bold text-slate-100">
              Pending Approval ({queue.length})
            </h2>
          </div>
          {queue.length > 0 && (
            <span className="text-xs px-2.5 py-1 rounded-full bg-indigo-500/10 text-indigo-400 font-medium border border-indigo-500/20">
              1-Tap Ready
            </span>
          )}
        </div>

        {/* Loading State */}
        {loading && (
          <div className="py-20 text-center space-y-3">
            <RefreshCw className="h-8 w-8 animate-spin mx-auto text-indigo-400" />
            <p className="text-sm text-slate-400">Synchronizing relationship queue...</p>
          </div>
        )}

        {/* Empty State */}
        {!loading && queue.length === 0 && (
          <div className="py-16 text-center space-y-4 px-6 rounded-3xl bg-slate-900/40 border border-dashed border-slate-800">
            <div className="h-14 w-14 rounded-2xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center mx-auto">
              <Check className="h-7 w-7" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">All Caught Up!</h3>
              <p className="text-xs text-slate-400 mt-1">
                Share a profile from the LinkedIn app, or discover builders to queue fresh drafts.
              </p>
            </div>
            <button
              onClick={() => setShowDiscoverModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30 transition"
            >
              <Search className="h-4 w-4" /> Discover AI Builders
            </button>
          </div>
        )}

        {/* Card Stack */}
        {!loading &&
          queue.map((item) => {
            const isConnectionNote = item.action_type === "connection_note";
            const charCount = item.content.length;
            const isOverLimit = isConnectionNote && charCount > 300;
            const relevanceScore = item.metadata?.relevance_score || 88;
            const contactName =
              item.contact?.full_name ||
              item.metadata?.builder?.name ||
              item.metadata?.builder?.github_username ||
              "Prospect Builder";
            const headline =
              item.contact?.headline ||
              item.metadata?.builder?.bio ||
              item.contact?.company ||
              "AI Engineer & Builder";
            const hooks = item.metadata?.hooks || ["Agentic Workflows", "LangGraph"];

            return (
              <div
                key={item.id}
                className="rounded-3xl bg-slate-900/90 border border-slate-800 p-4 shadow-xl space-y-3.5 transition active:border-slate-700"
              >
                {/* Card Header: Contact Info & Badge */}
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-1.5">
                      <h3 className="text-base font-bold text-white tracking-tight">{contactName}</h3>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        {relevanceScore}% Match
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 line-clamp-1">{headline}</p>
                  </div>

                  <span className="text-[11px] font-semibold px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 border border-slate-700 whitespace-nowrap">
                    {isConnectionNote ? "Connection Note" : item.action_type === "draft_comment" ? "Comment" : "Follow-Up"}
                  </span>
                </div>

                {/* Shared Hooks */}
                {hooks.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {hooks.map((hook, idx) => (
                      <span
                        key={idx}
                        className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20"
                      >
                        #{hook.replace(/^#/, "")}
                      </span>
                    ))}
                  </div>
                )}

                {/* Editable Draft Textarea */}
                <div className="relative">
                  <textarea
                    rows={3}
                    value={item.content}
                    onChange={(e) => handleDraftChange(item.id, e.target.value)}
                    className={`w-full rounded-2xl bg-slate-950 p-3 text-xs leading-relaxed text-slate-200 border resize-none focus:outline-none transition ${
                      isOverLimit
                        ? "border-rose-500 focus:ring-1 focus:ring-rose-500"
                        : "border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                    }`}
                  />
                  {/* Live Character Counter */}
                  <div className="flex items-center justify-between text-[11px] px-1 mt-1">
                    <span className="text-slate-500">Tap to edit before copy</span>
                    <span
                      className={`font-mono font-medium ${
                        isOverLimit ? "text-rose-400 font-bold flex items-center gap-1" : "text-slate-400"
                      }`}
                    >
                      {isOverLimit && <AlertTriangle className="h-3 w-3" />}
                      {charCount}{isConnectionNote ? "/300" : " chars"}
                    </span>
                  </div>
                </div>

                {/* Thumb-Friendly Action Buttons */}
                <div className="flex items-center gap-2 pt-1">
                  {/* Secondary Dismiss Button */}
                  <button
                    onClick={() => handleDismiss(item.id)}
                    className="p-3 rounded-2xl bg-slate-800/80 hover:bg-slate-800 text-slate-400 active:scale-95 transition"
                    aria-label="Dismiss draft"
                  >
                    <X className="h-4 w-4" />
                  </button>

                  {/* Primary 1-Tap Copy & Open Button */}
                  <button
                    onClick={() => handleCopyAndOpen(item)}
                    className="flex-1 py-3 px-4 rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 active:scale-[0.98] text-white text-xs font-bold shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2 transition"
                  >
                    {copiedId === item.id ? (
                      <>
                        <Check className="h-4 w-4 text-emerald-300" /> Copied & Approved!
                      </>
                    ) : (
                      <>
                        <Copy className="h-4 w-4" /> Copy & Open LinkedIn
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })}
      </main>

      {/* Discover Builders Modal */}
      {showDiscoverModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-end sm:items-center justify-center p-4">
          <div className="w-full max-w-sm rounded-3xl bg-slate-900 border border-slate-800 p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Search className="h-4 w-4 text-indigo-400" /> Discover AI Builders
              </h3>
              <button onClick={() => setShowDiscoverModal(false)} className="text-slate-400 p-1">
                <X className="h-4 w-4" />
              </button>
            </div>
            <p className="text-xs text-slate-400">
              Scans public AI/ML open-source repositories & profiles, auto-drafting connection requests.
            </p>
            <div className="space-y-1.5">
              <label className="text-[11px] font-semibold text-slate-300">Topic / Domain</label>
              <input
                type="text"
                value={discoverTopic}
                onChange={(e) => setDiscoverTopic(e.target.value)}
                className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                placeholder="e.g. agentic-ai, langgraph, fastapi"
              />
            </div>
            <button
              onClick={handleDiscover}
              disabled={discovering}
              className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition flex items-center justify-center gap-2"
            >
              {discovering ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              {discovering ? "Scanning Repositories..." : "Start Discovery"}
            </button>
          </div>
        </div>
      )}

      {/* New LinkedIn Post Modal */}
      {showPostModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-end sm:items-center justify-center p-4">
          <div className="w-full max-w-sm rounded-3xl bg-slate-900 border border-slate-800 p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <PenSquare className="h-4 w-4 text-indigo-400" /> New LinkedIn Post
              </h3>
              <button onClick={() => setShowPostModal(false)} className="text-slate-400 p-1">
                <X className="h-4 w-4" />
              </button>
            </div>
            <textarea
              rows={4}
              value={postContent}
              onChange={(e) => setPostContent(e.target.value)}
              placeholder="What do you want to share with your network?"
              className="w-full rounded-xl bg-slate-950 border border-slate-800 p-3 text-xs text-white focus:outline-none focus:border-indigo-500 resize-none"
            />
            <button
              onClick={handlePublishPost}
              disabled={publishing || !postContent.trim()}
              className="w-full py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-xs font-bold transition flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {publishing ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              {publishing ? "Publishing to Feed..." : "Publish Post"}
            </button>
          </div>
        </div>
      )}

      {/* Bottom Mobile Action & Navigation Bar */}
      <nav className="fixed bottom-0 left-0 right-0 z-30 max-w-md mx-auto bg-slate-950/90 backdrop-blur-xl border-t border-slate-800/80 px-4 py-2.5 flex items-center justify-around">
        <button
          onClick={() => setShowDiscoverModal(true)}
          className="flex flex-col items-center gap-1 text-slate-400 hover:text-white transition"
        >
          <Search className="h-5 w-5" />
          <span className="text-[10px] font-medium">Discover</span>
        </button>

        <button
          onClick={() => setShowPostModal(true)}
          className="flex flex-col items-center gap-1 text-slate-400 hover:text-white transition"
        >
          <PenSquare className="h-5 w-5" />
          <span className="text-[10px] font-medium">Post</span>
        </button>

        {installPrompt && (
          <button
            onClick={handleInstallClick}
            className="flex flex-col items-center gap-1 text-indigo-400 hover:text-indigo-300 transition"
          >
            <Download className="h-5 w-5" />
            <span className="text-[10px] font-bold">Install</span>
          </button>
        )}

        <button
          onClick={fetchQueue}
          className="flex flex-col items-center gap-1 text-slate-400 hover:text-white transition"
        >
          <RefreshCw className={`h-5 w-5 ${refreshing ? "animate-spin text-indigo-400" : ""}`} />
          <span className="text-[10px] font-medium">Refresh</span>
        </button>
      </nav>
    </div>
  );
}

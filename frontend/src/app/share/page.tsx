"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, Share2, CheckCircle2, AlertCircle, ArrowLeft } from "lucide-react";

function ShareHandlerContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"idle" | "analyzing" | "success" | "error">("idle");
  const [statusMessage, setStatusMessage] = useState("Processing shared content...");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    const rawUrl = searchParams.get("url") || "";
    const rawText = searchParams.get("text") || "";
    const rawTitle = searchParams.get("title") || "";

    if (!rawUrl && !rawText && !rawTitle) {
      setStatus("error");
      setErrorMessage("No URL or text received from the share sheet.");
      return;
    }

    // Extract any LinkedIn URL from text or url parameter
    const combined = `${rawUrl} ${rawText}`.trim();
    const urlMatch = combined.match(/https?:\/\/(www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_+.~#?&//=]*)/i);
    const targetUrl = urlMatch ? urlMatch[0] : rawUrl;
    const postOrNotes = rawText.replace(targetUrl, "").trim();

    async function analyzeSharedProfile() {
      setStatus("analyzing");
      setStatusMessage("Extracting profile & analyzing relationship hooks...");

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

      // Derive provisional name/headline from title or text
      let derivedName = rawTitle.replace(/\|.*$/i, "").trim() || "LinkedIn Connection";
      if (derivedName.length > 50) derivedName = "LinkedIn Connection";

      const payload = {
        full_name: derivedName,
        headline: rawTitle,
        linkedin_url: targetUrl || "https://linkedin.com",
        recent_post_text: postOrNotes || rawText || rawTitle,
        notes: `Shared from mobile PWA on ${new Date().toLocaleDateString()}`,
      };

      try {
        const res = await fetch(`${apiUrl}/api/analyze-profile`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          throw new Error(`Server returned ${res.status}: ${res.statusText}`);
        }

        const data = await res.json();
        setStatus("success");
        setStatusMessage("Draft generated & added to your queue!");

        // Brief delay before redirecting to queue
        setTimeout(() => {
          const actionId = data?.action_item?.id;
          router.push(actionId ? `/?focus=${actionId}` : "/");
        }, 1200);
      } catch (err: any) {
        console.error("Error analyzing shared profile:", err);
        setStatus("error");
        setErrorMessage(err.message || "Failed to analyze shared profile.");
      }
    }

    analyzeSharedProfile();
  }, [searchParams, router]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-6 text-center">
      <div className="w-full max-w-sm rounded-3xl bg-slate-900 border border-slate-800 p-8 shadow-2xl space-y-6">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
          {status === "analyzing" && <Loader2 className="h-8 w-8 animate-spin" />}
          {status === "success" && <CheckCircle2 className="h-8 w-8 text-emerald-400" />}
          {status === "error" && <AlertCircle className="h-8 w-8 text-rose-400" />}
          {status === "idle" && <Share2 className="h-8 w-8" />}
        </div>

        <div className="space-y-2">
          <h2 className="text-xl font-bold tracking-tight text-white">
            {status === "analyzing" && "Analyzing with AI"}
            {status === "success" && "Action Queued"}
            {status === "error" && "Unable to Process"}
            {status === "idle" && "Receiving Share"}
          </h2>
          <p className="text-sm text-slate-400">
            {status === "error" ? errorMessage : statusMessage}
          </p>
        </div>

        {status === "error" && (
          <button
            onClick={() => router.push("/")}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium transition"
          >
            <ArrowLeft className="h-4 w-4" /> Return to Queue
          </button>
        )}
      </div>
    </div>
  );
}

export default function SharePage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
        </div>
      }
    >
      <ShareHandlerContent />
    </Suspense>
  );
}

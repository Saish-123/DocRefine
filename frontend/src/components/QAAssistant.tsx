"use client";

import React, { useState, useRef, useEffect } from "react";
import { MessageSquare, Send, Bot, User, Sparkles, Loader2, HelpCircle } from "lucide-react";

interface QAAssistantProps {
  caseId: string;
  sessionToken?: string | null;
}

export const QAAssistant: React.FC<QAAssistantProps> = ({ caseId, sessionToken }) => {
  const [messages, setMessages] = useState<Array<{ sender: "user" | "bot"; text: string; citations?: any[] }>>([
    {
      sender: "bot",
      text: "Hello! I am your grounded document review assistant. Ask me questions regarding verified fields, candidate name, marks, PAN, Aadhaar details, or financial records in this case."
    }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSendQuery = async (queryText?: string) => {
    const userQuery = (queryText || input).trim();
    if (!userQuery || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { sender: "user", text: userQuery }]);
    setLoading(true);

    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (sessionToken) {
        headers["Authorization"] = `Bearer ${sessionToken}`;
      }

      const res = await fetch("/api/v1/qa/query", {
        method: "POST",
        headers,
        body: JSON.stringify({ case_id: caseId, query: userQuery })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData?.detail || `Server returned ${res.status}`);
      }

      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          text: data.answer || "Unable to answer from available evidence.",
          citations: data.citations || []
        }
      ]);
    } catch (err: any) {
      console.error("QA Query Error:", err);
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: `Unable to query document assistant: ${err.message || "Request failed"}` }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const quickPrompts = [
    "Summarize all extracted fields",
    "What is the candidate or party name?",
    "List marks, numbers & totals",
    "Check for any low-confidence fields"
  ];

  return (
    <div className="flex flex-col h-[380px] bg-slate-900/70 rounded-2xl border border-slate-800 overflow-hidden shadow-xl">
      {/* Header */}
      <div className="px-4 py-3 bg-slate-900/95 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="p-1 rounded-lg bg-violet-500/10 text-violet-400 border border-violet-500/20">
            <Bot className="h-4 w-4" />
          </div>
          <div>
            <span className="text-xs font-bold text-slate-100">DocRefine Grounded Q&amp;A</span>
            <span className="block text-[10px] text-slate-400">Strict evidence-based answers</span>
          </div>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-300 border border-violet-500/20">
          Zero Hallucination
        </span>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 p-3.5 overflow-y-auto space-y-3 text-xs">
        {messages.map((m, i) => (
          <div key={i} className={`flex items-start space-x-2 ${m.sender === "user" ? "justify-end" : "justify-start"}`}>
            {m.sender === "bot" && (
              <div className="p-1 rounded-lg bg-violet-950 border border-violet-700/40 text-violet-300 shrink-0 mt-0.5">
                <Bot className="h-3.5 w-3.5" />
              </div>
            )}
            <div
              className={`p-3 rounded-2xl max-w-[85%] leading-relaxed ${
                m.sender === "user"
                  ? "bg-violet-600 text-white rounded-br-sm shadow-md shadow-violet-600/20"
                  : "bg-slate-800/90 text-slate-200 border border-slate-700/70 rounded-bl-sm"
              }`}
            >
              <p className="whitespace-pre-line">{m.text}</p>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex items-center space-x-2 text-slate-400 text-xs pl-2">
            <Loader2 className="h-3.5 w-3.5 animate-spin text-violet-400" />
            <span>Consulting verified document records...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Prompts */}
      <div className="px-3 py-1.5 bg-slate-950/60 border-t border-slate-800/80 flex items-center gap-1.5 overflow-x-auto no-scrollbar">
        {quickPrompts.map((prompt, idx) => (
          <button
            key={idx}
            onClick={() => handleSendQuery(prompt)}
            disabled={loading}
            className="px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-[11px] text-slate-300 border border-slate-700 whitespace-nowrap transition disabled:opacity-50"
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Input Box */}
      <div className="p-2.5 bg-slate-950 border-t border-slate-800 flex items-center space-x-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSendQuery()}
          placeholder="Ask a question about this document case..."
          className="flex-1 bg-slate-900 border border-slate-700/80 rounded-xl px-3.5 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500 transition"
        />
        <button
          onClick={() => handleSendQuery()}
          disabled={loading || !input.trim()}
          className="p-2 rounded-xl bg-violet-600 hover:bg-violet-500 text-white transition disabled:opacity-50 shadow-md shadow-violet-600/20 active:scale-95"
        >
          <Send className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
};

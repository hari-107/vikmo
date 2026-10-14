import React, { useState, useEffect, useCallback, useRef } from "react";
import { useSearchParams, Link } from "react-router-dom";
import {
  Bot,
  User,
  Send,
  RefreshCw,
  Terminal,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  Cpu,
  Zap,
} from "lucide-react";
import { getDealers, sendAssistantMessage } from "../services/api";

const SUGGESTED_PROMPTS = [
  "Do you have brake pads for a Pulsar 150?",
  "Check available stock for BRK-1044",
  "Order 2 units of BRK-1044",
  "Do you have coolant for a Duke 390?",
  "Check inventory for OIL-1001",
];

export function Assistant() {
  const [searchParams] = useSearchParams();
  const queryDealerId = searchParams.get("dealer_id");

  // Dealers
  const [dealers, setDealers] = useState([]);
  const [selectedDealerId, setSelectedDealerId] = useState("");
  const [loadingDealers, setLoadingDealers] = useState(true);

  // Session
  const [sessionId, setSessionId] = useState(() => {
    let stored; try { stored = sessionStorage.getItem("vikmo_assistant_session"); } catch { /* Optional persistence. */ }
    if (stored) return stored;
    const created = `session-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    try { sessionStorage.setItem("vikmo_assistant_session", created); } catch { /* Optional persistence. */ }
    return created;
  });

  // Chat conversation
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [chatError, setChatError] = useState(null);

  // Collapsed tool calls state per message index
  const [expandedTools, setExpandedTools] = useState({});

  const messagesEndRef = useRef(null);



  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth" });
  }, [messages, isSending]);

  const fetchDealers = useCallback(async () => {
    setLoadingDealers(true);
    try {
      const res = await getDealers({ page_size: 50 });
      const list = res.results || [];
      setDealers(list);

      if (queryDealerId && list.some((d) => d.id.toString() === queryDealerId)) {
        setSelectedDealerId(queryDealerId);
      } else if (list.length > 0) {
        setSelectedDealerId(list[0].id.toString());
      }
    } catch (err) {
      setChatError(err.message || "Could not load dealers. Refresh to retry.");
    } finally {
      setLoadingDealers(false);
    }
  }, [queryDealerId]);

  const handleNewSession = () => {
    const newSession = `session-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
    sessionStorage.setItem("vikmo_assistant_session", newSession);
    setSessionId(newSession);
    setMessages([]);
    setChatError(null);
  };

  const toggleToolExpand = (msgIndex) => {
    setExpandedTools((prev) => ({
      ...prev,
      [msgIndex]: !prev[msgIndex],
    }));
  };

  const handleSendMessage = async (e) => {
    if (e) e.preventDefault();
    const cleanMsg = inputText.trim();
    if (!cleanMsg || isSending || !selectedDealerId) return;

    setInputText("");
    setChatError(null);

    const userTurn = {
      role: "user",
      content: cleanMsg,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userTurn]);
    setIsSending(true);

    try {
      const res = await sendAssistantMessage({
        sessionId,
        dealerId: parseInt(selectedDealerId, 10),
        message: cleanMsg,
      });

      const assistantTurn = {
        role: "assistant",
        content: res.reply || "",
        cited_skus: res.cited_skus || [],
        tool_calls: res.tool_calls || [],
        actions: res.actions || [],
        engine: res.engine || "deterministic",
        provider: res.provider || res.engine || "deterministic",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantTurn]);
    } catch (err) {
      setChatError(err.message || "Failed to communicate with assistant engine.");
    } finally {
      setIsSending(false);
    }
  };

  const currentDealer = dealers.find((d) => d.id.toString() === selectedDealerId);

  useEffect(() => {
    // Loading state tracks this external API request.
    // oxlint-disable-next-line react/set-state-in-effect
    fetchDealers();
  }, [fetchDealers]);

  return (
    <div className="assistant-panel flex flex-col h-[calc(100dvh-9rem)] max-w-5xl mx-auto panel rounded-xl border border-line shadow-xs overflow-hidden">
      {/* Top Bar: Session & Dealer Info */}
      <div className="px-6 py-4 bg-surface border-b border-line flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center text-on-primary font-bold shadow-xs">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <div className="font-display font-bold text-base text-foreground tracking-tight flex items-center gap-2">
              VIKMO AI Commerce Assistant
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-primary-soft text-primary-hover border border-line">
                Live catalogue
              </span>
            </div>
            <div className="text-xs text-secondary">
              Find compatible parts, check stock, and create dealer draft orders.
            </div>
          </div>
        </div>

        {/* Dealer Selector & New Session */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-surface px-3 py-1.5 rounded-full border border-line">
            <span className="text-xs font-medium text-secondary">Acting as:</span>
            {loadingDealers ? (
              <span className="text-xs text-secondary">Loading...</span>
            ) : (
              <select
                disabled={isSending}
                aria-label="Dealer for conversation"
                value={selectedDealerId}
                onChange={(e) => {
                  const newId = e.target.value;
                  setSelectedDealerId(newId);
                  const freshSession = `session-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
                  sessionStorage.setItem("vikmo_assistant_session", freshSession);
                  setSessionId(freshSession);
                  setMessages([]);
                  setChatError(null);
                }}
                className="text-xs bg-transparent text-foreground font-semibold focus:outline-none cursor-pointer"
              >
                {dealers.map((d) => (
                  <option key={d.id} value={d.id} className="bg-surface text-foreground">
                    {d.dealer_code} — {d.name}
                  </option>
                ))}
              </select>
            )}
          </div>

          <button
            disabled={isSending}
            onClick={handleNewSession}
            className="btn-secondary rounded-full px-3 py-1.5 text-xs flex items-center gap-1.5 shadow-2xs"
            title="Reset conversation and start fresh session"
          >
            <RefreshCw className="w-3.5 h-3.5 text-primary" />
            <span>New Chat</span>
          </button>
        </div>
      </div>

      {/* Messages Timeline */}
      <div className="flex-1 p-6 overflow-y-auto space-y-4 bg-canvas/40">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-4">
            <div className="w-14 h-14 rounded-lg bg-primary-soft flex items-center justify-center text-primary shadow-2xs">
              <Sparkles className="w-7 h-7" />
            </div>
            <div className="max-w-md">
              <h3 className="font-display font-bold text-2xl text-foreground">
                How can I assist your dealership today?
              </h3>
              <p className="text-xs text-secondary mt-1.5 leading-relaxed">
                I can look up parts from your live catalogue, check real-time warehouse stock, and create draft orders directly on behalf of{" "}
                <span className="font-semibold text-foreground">
                  {currentDealer ? currentDealer.name : "your dealership"}
                </span>
                .
              </p>
            </div>

            {/* Quick Prompts */}
            <div className="flex flex-wrap justify-center gap-2 max-w-lg pt-2">
              {SUGGESTED_PROMPTS.map((prompt, i) => (
                <button
                  key={i}
                  onClick={() => {
                    setInputText(prompt);
                  }}
                  className="px-4 py-2 text-xs font-medium bg-surface hover:bg-primary hover:text-on-primary text-foreground border border-line rounded-full transition-all duration-200 shadow-2xs cursor-pointer"
                >
                  "{prompt}"
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, idx) => {
            const isUser = msg.role === "user";
            return (
              <div
                key={idx}
                className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}
              >
                {!isUser && (
                  <div className="w-8 h-8 rounded-xl bg-primary flex items-center justify-center text-on-primary font-bold shrink-0 mt-1 shadow-2xs">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div
                  className={`max-w-2xl rounded-lg p-4 space-y-2.5 shadow-2xs ${
                    isUser
                      ? "bg-primary text-on-primary rounded-tr-xs"
                      : "bg-surface text-foreground border border-line rounded-tl-xs"
                  }`}
                >
                  {/* Engine Indicator Header */}
                  {!isUser && (
                    <div className="flex items-center justify-between pb-2 border-b border-line/60 mb-1">
                      <span className="text-[10px] font-bold text-secondary uppercase tracking-wider">
                        VIKMO Assistant
                      </span>
                      {(msg.provider === "gemini" || msg.engine === "gemini") ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-success-soft text-success-ink border border-success-line">
                          <Sparkles className="w-2.5 h-2.5 text-success-ink" />
                          Gemini Live
                        </span>
                      ) : (msg.provider === "groq" || msg.engine === "groq") ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-primary-soft text-primary-hover border border-line">
                          <Zap className="w-2.5 h-2.5 text-primary-hover" />
                          Groq Live
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-subtle text-secondary border border-line">
                          <Cpu className="w-2.5 h-2.5 text-secondary" />
                          Deterministic Fallback
                        </span>
                      )}
                    </div>
                  )}

                  {/* Message Content */}
                  <div className="text-sm leading-relaxed whitespace-pre-wrap">
                    {msg.content}
                  </div>

                  {/* Actions Result Box (e.g. Draft Order Created) */}
                  {!isUser && msg.actions && msg.actions.length > 0 && (
                    <div className="space-y-1.5 pt-1">
                      {msg.actions.map((act, aIdx) => (
                        <div
                          key={aIdx}
                          className="flex items-center justify-between p-3 rounded-xl bg-success-soft border border-success-line text-success-ink text-xs shadow-2xs"
                        >
                          <div className="flex items-center gap-2">
                            <CheckCircle2 className="w-4 h-4 text-success-ink shrink-0" />
                            <div>
                              <span className="font-semibold">Draft Order Created: </span>
                              <span className="font-mono font-bold text-foreground">
                                {act.order_number}
                              </span>
                            </div>
                          </div>
                          <Link
                            to={`/orders?order=${act.order_number}`}
                            className="inline-flex items-center gap-1 font-semibold text-primary hover:text-primary-hover hover:underline"
                          >
                            <span>Inspect Order</span>
                            <ExternalLink className="w-3 h-3" />
                          </Link>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Cited SKUs Badges */}
                  {!isUser && msg.cited_skus && msg.cited_skus.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5 pt-1">
                      <span className="text-[11px] font-semibold text-secondary">
                        Cited Catalogue SKUs:
                      </span>
                      {msg.cited_skus.map((sku) => (
                        <Link
                          key={sku}
                          to={`/products?search=${sku}`}
                          className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-primary-soft text-primary-hover border border-line hover:bg-primary hover:text-on-primary transition-colors"
                        >
                          {sku}
                        </Link>
                      ))}
                    </div>
                  )}

                  {/* Tool Calls Inspector Dropdown */}
                  {!isUser && msg.tool_calls && msg.tool_calls.length > 0 && (
                    <div className="pt-1.5 border-t border-line/60">
                      <button
                        onClick={() => toggleToolExpand(idx)}
                        className="flex items-center gap-1.5 text-[11px] font-semibold text-secondary hover:text-foreground transition-colors cursor-pointer"
                      >
                        <Terminal className="w-3.5 h-3.5 text-secondary" />
                        <span>
                          Executed {msg.tool_calls.length} Tool Call(s)
                        </span>
                        {expandedTools[idx] ? (
                          <ChevronDown className="w-3 h-3 text-secondary" />
                        ) : (
                          <ChevronRight className="w-3 h-3 text-secondary" />
                        )}
                      </button>

                      {expandedTools[idx] && (
                        <div className="mt-2 space-y-1.5 p-3 bg-subtle text-foreground rounded-xl text-xs font-mono border border-line-strong">
                          {msg.tool_calls.map((tc, tIdx) => (
                            <div key={tIdx} className="space-y-0.5 pb-1 border-b border-line-strong last:border-0">
                              <div className="text-primary font-bold">
                                {tIdx + 1}. {tc.name}()
                              </div>
                              <div className="text-[11px] text-secondary overflow-x-auto">
                                args: {JSON.stringify(tc.arguments)}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {isUser && (
                  <div className="w-8 h-8 rounded-xl bg-subtle border border-line flex items-center justify-center text-secondary font-bold shrink-0 mt-1 shadow-2xs">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            );
          })
        )}

        {/* Sending / Thinking Indicator */}
        {isSending && (
          <div className="flex gap-3 justify-start items-center">
            <div className="w-8 h-8 rounded-xl bg-primary flex items-center justify-center text-on-primary font-bold shrink-0">
              <Bot className="w-4 h-4" />
            </div>
            <div className="bg-surface border border-line rounded-lg rounded-tl-xs px-4 py-3 shadow-2xs flex items-center gap-2 text-xs text-secondary font-medium">
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-primary" />
              <span>Checking parts catalogue & reasoning with live tools...</span>
            </div>
          </div>
        )}

        {chatError && (
          <div className="p-3.5 bg-danger-soft border border-danger-line rounded-xl text-danger text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-danger" />
            <span>{chatError}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <div className="p-4 bg-surface border-t border-line">
        <form onSubmit={handleSendMessage} className="flex gap-2">
          <input
            aria-label="Message to assistant"
            type="text"
            value={inputText}
            disabled={isSending || !selectedDealerId}
            onChange={(e) => setInputText(e.target.value)}
            placeholder={
              selectedDealerId
                ? "Ask about parts, inventory availability, or say 'Order 2 units of BRK-1044'..."
                : "Select a dealer above to begin chat..."
            }
            className="flex-1 px-4 py-2.5 form-control bg-surface border border-line text-foreground placeholder-secondary rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary transition-colors"
          />
          <button
            type="submit"
            disabled={!inputText.trim() || isSending || !selectedDealerId}
            className="btn-primary rounded-lg px-5 py-2.5 flex items-center gap-2 shadow-xs cursor-pointer disabled:opacity-40"
          >
            <Send className="w-4 h-4 text-on-primary" />
            <span>Send</span>
          </button>
        </form>
        <div className="mt-2 text-[11px] text-secondary flex flex-wrap gap-2 items-center justify-between">
          <span title={`Session: ${sessionId}`}>Live catalogue and stock availability</span>
          <span>Orders are saved as drafts for review.</span>
        </div>
      </div>
    </div>
  );
}

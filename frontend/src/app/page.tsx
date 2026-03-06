"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search, Loader2, BarChart2, Radio, Megaphone, Users, ChevronRight,
  Mail, CheckCircle, X, Download, FileText, TrendingUp, Package,
  DollarSign, Globe, ShieldCheck, Zap, LineChart,
  Briefcase, Handshake, Target, AlertTriangle,
  Fingerprint, UserSearch
} from "lucide-react";
import axios from "axios";

// ── Types ────────────────────────────────────────────────────────────────
type InsightItem = {
  title: string;
  detail: string;
  date: string;
  source_url: string;
} | string;

type InsightsData = {
  companyName: string;
  pr: InsightItem[];
  podcasts: InsightItem[];
  ads: InsightItem[];
  influencers: InsightItem[];
  social_media: InsightItem[];
  market_analysis: InsightItem[];
  product_roadmap: InsightItem[];
  financial: InsightItem[];
  hiring_signals: InsightItem[];
  partnerships: InsightItem[];
  strategic_recommendations: InsightItem[];
  risk_assessment: InsightItem[];
  digital_footprint: InsightItem[];
  talent_intelligence: InsightItem[];
  _source?: string;
  _sources_count?: number;
  _news_count?: number;
};

// ── Shared UI Components ─────────────────────────────────────────────────
function Navbar() {
  return (
    <nav className="w-full border-b border-white/5 bg-[#06060a]/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
            <Search className="w-4 h-4 text-white" />
          </div>
          <span className="text-xl font-bold tracking-tight text-white">Sneak</span>
        </div>
      </div>
    </nav>
  );
}

function Footer() {
  return (
    <footer className="w-full border-t border-white/5 bg-[#06060a] mt-24">
      <div className="max-w-7xl mx-auto px-6 py-12 flex flex-col md:flex-row justify-between items-center gap-6">
        <div className="flex items-center gap-2 opacity-50">
          <Search className="w-4 h-4" />
          <span className="font-bold tracking-tight">Sneak Intelligence</span>
        </div>
        <div className="flex gap-6 text-sm text-zinc-500">
          <a href="#" className="hover:text-zinc-300 transition-colors">Privacy</a>
          <a href="#" className="hover:text-zinc-300 transition-colors">Terms</a>
          <a href="#" className="hover:text-zinc-300 transition-colors">Status</a>
          <a href="#" className="hover:text-zinc-300 transition-colors">Security</a>
        </div>
        <p className="text-sm text-zinc-600">© 2026 Sneak Inc. All rights reserved.</p>
      </div>
    </footer>
  );
}

function TrustBadges() {
  return (
    <div className="flex flex-wrap justify-center gap-6 md:gap-12 mt-12 opacity-60">
      <div className="flex items-center gap-2 text-sm text-zinc-400">
        <Zap className="w-4 h-4 text-emerald-400" /> Real-time OSINT Data
      </div>
      <div className="flex items-center gap-2 text-sm text-zinc-400">
        <LineChart className="w-4 h-4 text-blue-400" /> 8 Intelligence Categories
      </div>
      <div className="flex items-center gap-2 text-sm text-zinc-400">
        <ShieldCheck className="w-4 h-4 text-purple-400" /> Enterprise-Grade Security
      </div>
    </div>
  );
}

function StatsBar({ data }: { data: InsightsData }) {
  const getCount = (arr: InsightItem[]) => (Array.isArray(arr) ? arr.length : 0);
  const totalInsights =
    getCount(data.pr) +
    getCount(data.podcasts) +
    getCount(data.ads) +
    getCount(data.influencers) +
    getCount(data.social_media) +
    getCount(data.market_analysis) +
    getCount(data.product_roadmap) +
    getCount(data.financial);

  const activeCategories = [
    data.pr, data.podcasts, data.ads, data.influencers,
    data.social_media, data.market_analysis, data.product_roadmap, data.financial
  ].filter(arr => getCount(arr) > 0).length;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="w-full max-w-7xl grid grid-cols-1 md:grid-cols-3 gap-6 mb-12"
    >
      <div className="glass rounded-xl p-5 flex flex-col justify-center">
        <span className="text-zinc-400 text-sm font-medium mb-1">Total Insights Extracted</span>
        <div className="text-4xl font-bold text-white stat-number">{totalInsights}</div>
      </div>
      <div className="glass rounded-xl p-5 flex flex-col justify-center">
        <span className="text-zinc-400 text-sm font-medium mb-1">Categories Analyzed</span>
        <div className="text-4xl font-bold text-white stat-number">{activeCategories}<span className="text-lg text-zinc-600">/8</span></div>
      </div>
      <div className="glass rounded-xl p-5 flex flex-col justify-center">
        <span className="text-zinc-400 text-sm font-medium mb-1">Confidence Score</span>
        <div className="text-4xl font-bold text-emerald-400 stat-number">94<span className="text-lg text-emerald-600">%</span></div>
      </div>
    </motion.div>
  );
}

// ── Main Page Component ──────────────────────────────────────────────────
export default function Home() {
  const [company, setCompany] = useState("");
  const [status, setStatus] = useState<string>("idle");
  const [insights, setInsights] = useState<InsightsData | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Email state
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [emailInput, setEmailInput] = useState("");
  const [emailSubmitted, setEmailSubmitted] = useState(false);
  const [emailDismissed, setEmailDismissed] = useState(false);
  const [emailSending, setEmailSending] = useState(false);

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!company) return;

    setStatus("starting");
    setInsights(null);
    setErrorMessage(null);
    setCurrentJobId(null);
    setEmailInput("");
    setEmailSubmitted(false);
    setEmailDismissed(false);

    try {
      const analyzeResponse = await axios.post(`${apiBaseUrl}/analyze`, { company_name: company });
      const createdJobId = analyzeResponse.data?.job_id;
      if (!createdJobId) throw new Error("Job ID missing from API response");
      setCurrentJobId(createdJobId);
      setStatus(analyzeResponse.data?.status || "pending");

      for (let attempt = 0; attempt < 90; attempt++) {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        const jobResponse = await axios.get(`${apiBaseUrl}/jobs/${createdJobId}`);
        const jobStatus = jobResponse.data?.status;
        setStatus(jobStatus || "pending");

        if (jobStatus === "completed") {
          const result = jobResponse.data?.result || {};
          if (result.error) throw new Error(result.error);
          setInsights({
            companyName: result.companyName || company,
            pr: Array.isArray(result.pr) ? result.pr : [],
            podcasts: Array.isArray(result.podcasts) ? result.podcasts : [],
            ads: Array.isArray(result.ads) ? result.ads : [],
            influencers: Array.isArray(result.influencers) ? result.influencers : [],
            social_media: Array.isArray(result.social_media) ? result.social_media : [],
            market_analysis: Array.isArray(result.market_analysis) ? result.market_analysis : [],
            product_roadmap: Array.isArray(result.product_roadmap) ? result.product_roadmap : [],
            financial: Array.isArray(result.financial) ? result.financial : [],
            hiring_signals: Array.isArray(result.hiring_signals) ? result.hiring_signals : [],
            partnerships: Array.isArray(result.partnerships) ? result.partnerships : [],
            strategic_recommendations: Array.isArray(result.strategic_recommendations) ? result.strategic_recommendations : [],
            risk_assessment: Array.isArray(result.risk_assessment) ? result.risk_assessment : [],
            digital_footprint: Array.isArray(result.digital_footprint) ? result.digital_footprint : [],
            talent_intelligence: Array.isArray(result.talent_intelligence) ? result.talent_intelligence : [],
            _source: result._source || "ai",
            _sources_count: result._sources_count,
            _news_count: result._news_count,
          });
          return;
        }

        if (jobStatus === "failed") throw new Error(jobResponse.data?.result?.error || "Job failed");
      }
      throw new Error("Timed out waiting for insights generation");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Something went wrong.";
      setErrorMessage(msg);
      setStatus("error");
    }
  };

  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!emailInput || !currentJobId) return;
    setEmailSending(true);
    try {
      await axios.patch(`${apiBaseUrl}/jobs/${currentJobId}/email`, { email: emailInput });
      setEmailSubmitted(true);
    } catch { }
    finally { setEmailSending(false); }
  };

  const showEmailPrompt = status === "waiting_for_ai" && !emailSubmitted && !emailDismissed && currentJobId !== null;

  return (
    <>
      <Navbar />
      <main className="flex min-h-[calc(100vh-64px)] flex-col items-center justify-start p-6 md:p-16 relative overflow-hidden">

        {/* Ambient B2B Orbs */}
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-blue-600/10 blur-[120px] rounded-full pointer-events-none float-orb" />
        <div className="absolute bottom-[20%] right-[-10%] w-[40%] h-[50%] bg-purple-600/10 blur-[120px] rounded-full pointer-events-none float-orb" style={{ animationDelay: "-10s" }} />

        <div className="z-10 w-full max-w-7xl flex flex-col items-center gap-10 min-h-[60vh] justify-center pt-10 pb-20">

          {/* Hero Section */}
          <AnimatePresence mode="wait">
            {(status === "idle" || status === "error") && (
              <motion.div
                key="hero"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20, filter: "blur(10px)" }}
                className="w-full flex flex-col items-center"
              >
                <div className="text-center space-y-6 mb-12">
                  <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-blue-500/20 bg-blue-500/10 text-sm font-medium text-blue-200">
                    <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
                    Enterprise Intelligence Platform
                  </div>
                  <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight leading-[1.1]">
                    Reveal the invisible strategies <br className="hidden md:block" />
                    of <span className="gradient-text">any competitor.</span>
                  </h1>
                  <p className="text-zinc-400 text-lg md:text-xl max-w-2xl mx-auto font-medium">
                    Instantly synthesize scattered PR, podcasts, financials, and social data into board-ready competitive intelligence.
                  </p>
                </div>

                <form onSubmit={handleAnalyze} className="w-full max-w-3xl relative">
                  <div className="relative group">
                    <div className="absolute inset-0 bg-gradient-to-r from-blue-500/30 to-purple-500/30 rounded-2xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
                    <div className="relative flex items-center bg-[#0d0d12] border border-white/10 rounded-2xl p-2.5 shadow-2xl">
                      <Search className="w-6 h-6 text-zinc-500 ml-4 hidden sm:block" />
                      <input
                        type="text"
                        value={company}
                        onChange={(e) => setCompany(e.target.value)}
                        placeholder="Target company (e.g., Stripe, Tesla, OpenAI)"
                        className="w-full bg-transparent border-none outline-none text-xl px-4 py-4 text-white placeholder:text-zinc-600"
                        autoFocus
                      />
                      <button
                        type="submit"
                        disabled={!company}
                        className="bg-white text-black px-8 py-4 rounded-xl font-bold hover:bg-zinc-200 transition-colors disabled:opacity-50 flex items-center gap-2 tracking-tight"
                      >
                        Generate Report
                      </button>
                    </div>
                  </div>
                </form>

                <TrustBadges />

                {/* Error Banner */}
                {status === "error" && errorMessage && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="mt-8 bg-red-900/20 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm flex items-center gap-3"
                  >
                    <X className="w-4 h-4" /> {errorMessage}
                  </motion.div>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Loading Pipeline */}
          <AnimatePresence>
            {status !== "idle" && status !== "completed" && status !== "error" && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95, filter: "blur(5px)" }}
                className="w-full max-w-3xl glass rounded-2xl p-8 overflow-hidden relative shadow-2xl"
              >
                <div className="absolute top-0 left-0 w-full h-1 bg-white/5">
                  <motion.div
                    className="h-full bg-gradient-to-r from-blue-500 to-purple-500"
                    initial={{ width: "0%" }}
                    animate={{
                      width: status === "starting" ? "5%" :
                        status === "collecting_data" ? "20%" :
                          status === "scraping" ? "40%" :
                            status === "extracting_content" ? "60%" :
                              status === "generating_insights" ? "80%" :
                                status === "waiting_for_ai" ? "92%" : "98%"
                    }}
                    transition={{ ease: "easeInOut", duration: 1 }}
                  />
                </div>
                <div className="flex items-center gap-6">
                  <div className="w-14 h-14 rounded-full bg-blue-500/10 flex items-center justify-center shrink-0">
                    <Loader2 className="w-7 h-7 text-blue-400 animate-spin" />
                  </div>
                  <div className="flex flex-col gap-1">
                    <h2 className="text-xl font-bold text-white tracking-tight">Synthesizing Intelligence</h2>
                    <p className="text-zinc-400 font-medium">
                      {status === "starting" && "Initializing deep intelligence pipeline..."}
                      {status === "pending" && "Queued — allocating worker..."}
                      {status === "collecting_data" && "Running OSINT scan, SearXNG, Google News, and website crawler in parallel..."}
                      {status === "scraping" && "Deep-scraping 25+ sources with structured data extraction..."}
                      {status === "extracting_content" && "Parsing JSON-LD, OpenGraph, tech stack, subdomains, and key facts..."}
                      {status === "generating_insights" && "Feeding enriched OSINT data to strategic AI analyst..."}
                      {status === "waiting_for_ai" && "Generating board-ready intelligence across 14 categories..."}
                    </p>
                  </div>
                </div>

                {/* Email Prompt */}
                <AnimatePresence>
                  {showEmailPrompt && (
                    <motion.div
                      initial={{ opacity: 0, height: 0, marginTop: 0 }}
                      animate={{ opacity: 1, height: "auto", marginTop: 32 }}
                      exit={{ opacity: 0, height: 0, marginTop: 0 }}
                      className="border-t border-white/5 pt-6"
                    >
                      <div className="flex items-start gap-4 p-5 rounded-xl bg-purple-500/10 border border-purple-500/20">
                        <Mail className="w-5 h-5 text-purple-400 shrink-0 mt-0.5" />
                        <div className="flex-1">
                          <h3 className="font-semibold text-white mb-1">Send me the PDF</h3>
                          <p className="text-sm text-purple-200/70 mb-4">Deep analysis can take up to 60 seconds. We can email you the final PDF report.</p>
                          <form onSubmit={handleEmailSubmit} className="flex gap-2">
                            <input
                              type="email"
                              value={emailInput}
                              onChange={(e) => setEmailInput(e.target.value)}
                              placeholder="work@email.com"
                              required
                              className="flex-1 bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-sm text-white focus:border-purple-500/50 outline-none"
                            />
                            <button
                              type="submit"
                              disabled={emailSending || !emailInput}
                              className="bg-purple-500 hover:bg-purple-600 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors disabled:opacity-50 flex items-center gap-2"
                            >
                              {emailSending ? <Loader2 className="w-4 h-4 animate-spin" /> : null} Set Alert
                            </button>
                          </form>
                        </div>
                        <button onClick={() => setEmailDismissed(true)} className="text-zinc-500 hover:text-white"><X className="w-4 h-4" /></button>
                      </div>
                    </motion.div>
                  )}
                  {emailSubmitted && (status === "waiting_for_ai" || status === "generating_insights") && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-6 flex items-center gap-2 text-emerald-400 text-sm font-medium bg-emerald-500/10 p-3 rounded-lg border border-emerald-500/20">
                      <CheckCircle className="w-4 h-4" /> PDF report will be sent to {emailInput}
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Results Dashboard */}
          {status === "completed" && insights && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="w-full flex flex-col gap-6"
            >
              <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-4">
                <div>
                  <h1 className="text-3xl md:text-5xl font-extrabold text-white tracking-tight mb-2">
                    {insights.companyName}
                  </h1>
                  <p className="text-zinc-400 font-medium">Real-time Intelligence Report</p>
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={() => { setStatus("idle"); setCompany(""); }}
                    className="px-5 py-2.5 rounded-xl border border-white/10 text-white font-medium hover:bg-white/5 transition-colors"
                  >
                    New Search
                  </button>
                  <a
                    href={`${apiBaseUrl}/jobs/${currentJobId}/report`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 bg-white text-black px-6 py-2.5 rounded-xl font-bold hover:bg-zinc-200 transition-colors shadow-[0_0_20px_rgba(255,255,255,0.2)]"
                  >
                    <Download className="w-4 h-4" /> Download PDF
                  </a>
                </div>
              </div>

              <StatsBar data={insights} />

              {(insights._source === "local_summarizer" || insights._source === "error") && (
                <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl px-5 py-4 text-amber-200 text-sm font-medium flex items-center gap-3">
                  <ShieldCheck className="w-5 h-5 text-amber-400 shrink-0" />
                  Premium AI models are currently overwhelmed. Showing fallback keyword-extracted insights (less detail).
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full pattern-dots">
                <InsightCard title="Strategic Recommendations" delay={0.05} borderClass="accent-border-emerald" icon={<Target className="w-5 h-5 text-emerald-400" />} items={insights.strategic_recommendations} />
                <InsightCard title="Risk Assessment" delay={0.1} borderClass="accent-border-red" icon={<AlertTriangle className="w-5 h-5 text-red-400" />} items={insights.risk_assessment} />
                <InsightCard title="Market Analysis" delay={0.15} borderClass="accent-border-cyan" icon={<TrendingUp className="w-5 h-5 text-cyan-400" />} items={insights.market_analysis} />
                <InsightCard title="Financial & Funding" delay={0.2} borderClass="accent-border-emerald" icon={<DollarSign className="w-5 h-5 text-emerald-400" />} items={insights.financial} />
                <InsightCard title="Hiring Signals" delay={0.25} borderClass="accent-border-teal" icon={<Briefcase className="w-5 h-5 text-teal-400" />} items={insights.hiring_signals} />
                <InsightCard title="Strategic Partnerships" delay={0.3} borderClass="accent-border-violet" icon={<Handshake className="w-5 h-5 text-violet-400" />} items={insights.partnerships} />
                <InsightCard title="Product Roadmap" delay={0.35} borderClass="accent-border-indigo" icon={<Package className="w-5 h-5 text-indigo-400" />} items={insights.product_roadmap} />
                <InsightCard title="PR & Announcements" delay={0.4} borderClass="accent-border-blue" icon={<Megaphone className="w-5 h-5 text-blue-400" />} items={insights.pr} />
                <InsightCard title="Podcast Appearances" delay={0.45} borderClass="accent-border-purple" icon={<Radio className="w-5 h-5 text-purple-400" />} items={insights.podcasts} />
                <InsightCard title="Social Media Activity" delay={0.5} borderClass="accent-border-pink" icon={<Globe className="w-5 h-5 text-pink-400" />} items={insights.social_media} />
                <InsightCard title="Ad Campaigns" delay={0.55} borderClass="accent-border-orange" icon={<BarChart2 className="w-5 h-5 text-orange-400" />} items={insights.ads} />
                <InsightCard title="Influencer Collabs" delay={0.6} borderClass="accent-border-amber" icon={<Users className="w-5 h-5 text-amber-400" />} items={insights.influencers} />
                <InsightCard title="Digital Footprint" delay={0.65} borderClass="accent-border-teal" icon={<Fingerprint className="w-5 h-5 text-teal-400" />} items={insights.digital_footprint} />
                <InsightCard title="Talent Intelligence" delay={0.7} borderClass="accent-border-violet" icon={<UserSearch className="w-5 h-5 text-violet-400" />} items={insights.talent_intelligence} />
              </div>
            </motion.div>
          )}

        </div>
      </main>
      <Footer />
    </>
  );
}

// ── Insight Card Component ───────────────────────────────────────────────
function InsightCard({ title, icon, items, borderClass, delay }: { title: string, icon: React.ReactNode, items: InsightItem[], borderClass: string, delay: number }) {
  if (items.length === 0) return null;
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.5, ease: "easeOut" }}
      className={`glass rounded-2xl p-7 flex flex-col ${borderClass} shadow-xl relative overflow-hidden group`}
    >
      <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:scale-110 group-hover:opacity-10 transition-all duration-500 ease-out z-0 pointer-events-none">
        {React.cloneElement(icon as React.ReactElement<any>, { className: "w-32 h-32" })}
      </div>

      <div className="flex items-center gap-4 mb-6 relative z-10">
        <div className="p-3 rounded-lg bg-black/40 border border-white/5 shadow-inner">
          {icon}
        </div>
        <h3 className="text-xl font-bold text-white tracking-tight">{title}</h3>
      </div>

      <ul className="space-y-4 relative z-10">
        {items.map((item, idx) => {
          if (typeof item === "string") {
            return (
              <li key={idx} className="flex gap-3 text-zinc-300">
                <ChevronRight className="w-4 h-4 text-zinc-600 shrink-0 mt-1" />
                <span className="leading-relaxed font-medium">{item}</span>
              </li>
            );
          }
          return (
            <li key={idx} className="bg-black/20 border border-white/5 rounded-xl p-5 hover:bg-black/40 transition-colors">
              {item.title && <h4 className="font-bold text-white text-base mb-2 tracking-tight">{item.title}</h4>}
              {item.detail && <p className="text-zinc-400 text-sm leading-relaxed mb-3 font-medium">{item.detail}</p>}
              <div className="flex flex-wrap items-center gap-3 mt-1">
                {item.date && (
                  <span className="text-[11px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-md bg-white/5 text-zinc-300">
                    {item.date}
                  </span>
                )}
                {item.source_url && (
                  <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="text-xs font-semibold text-blue-400 hover:text-blue-300 underline underline-offset-4 truncate max-w-[200px]">
                    {item.source_url.replace(/^https?:\/\/(www\.)?/, "").split("/")[0]}
                  </a>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </motion.div>
  );
}

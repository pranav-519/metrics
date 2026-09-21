import React, { useState, useEffect } from 'react';
import { BookOpen, ShieldCheck, Filter, Search, Tag, Calendar, AlertCircle } from 'lucide-react';

export default function RulesExplorerPage({ categories = [] }) {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    fetchRules();
  }, [selectedCategory]);

  const fetchRules = async () => {
    setLoading(true);
    try {
      let url = "/api/rules";
      if (selectedCategory !== "ALL") {
        url += `?category_code=${selectedCategory}`;
      }
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setRules(data);
      }
    } catch (e) {
      console.error("Failed to load legal rules:", e);
    } finally {
      setLoading(false);
    }
  };

  const filteredRules = rules.filter(r => {
    const q = searchQuery.toLowerCase();
    return r.rule_id.toLowerCase().includes(q) ||
           r.field_target.toLowerCase().includes(q) ||
           r.requirement.toLowerCase().includes(q) ||
           r.rule_reference.toLowerCase().includes(q);
  });

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header Banner */}
      <div className="bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-xs space-y-3">
        <div className="flex items-center gap-2 text-blue-700 text-xs font-semibold uppercase tracking-wider">
          <BookOpen className="w-4 h-4" />
          <span>Statutory Rule Base Architecture</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold text-slate-900">Legal Metrology Rules Engine</h1>
        <p className="text-sm text-slate-600 max-w-3xl leading-relaxed">
          Statutory declarations are evaluated against versioned, category-specific rules. 
          Rules are decoupled from frontend views to support regulatory amendments, gazette notifications, and state-specific variations.
        </p>

        {/* Legal Disclaimer Note */}
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-3.5 text-xs text-amber-900 flex items-start gap-2.5 mt-4">
          <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <p>
            <strong>Statutory Reference Notice:</strong> Configured records reference the Legal Metrology (Packaged Commodities) Rules, 2011 
            as amended. Where exact legal verification is not connected, demo/placeholder schedules are clearly designated.
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-500" />
          <span className="text-xs font-semibold text-slate-700">Category Filter:</span>
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 font-medium text-slate-800 cursor-pointer"
          >
            <option value="ALL">All Commodities (General + Specific)</option>
            {categories.map((c) => (
              <option key={c.code} value={c.code}>
                {c.name}
              </option>
            ))}
          </select>
        </div>

        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search clause or field..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 w-full sm:w-64 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Rules List */}
      {loading ? (
        <div className="p-12 text-center text-slate-500 text-sm">
          Loading legal rules...
        </div>
      ) : filteredRules.length === 0 ? (
        <div className="p-12 text-center text-slate-500 text-sm">
          No compliance rules found for this query.
        </div>
      ) : (
        <div className="space-y-4">
          {filteredRules.map((rule) => (
            <div key={rule.rule_id} className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                    {rule.rule_id}
                  </span>
                  <span className="text-xs font-semibold text-slate-800">
                    Target: {rule.field_target.toUpperCase()}
                  </span>
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-medium">
                    {rule.category_name || "All Commodities"}
                  </span>
                </div>

                <div className="flex items-center gap-2 text-xs">
                  <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-bold">
                    ACTIVE
                  </span>
                  <span className="text-slate-400 font-mono">v{rule.version}</span>
                </div>
              </div>

              {/* Requirement */}
              <div className="text-xs space-y-1">
                <span className="font-bold text-slate-700 uppercase text-[10px] tracking-wider">Mandatory Requirement:</span>
                <p className="text-slate-800 leading-relaxed font-medium bg-slate-50 p-3 rounded-lg border border-slate-200/60">
                  {rule.requirement}
                </p>
              </div>

              {/* Rule Meta */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-2 text-[11px] text-slate-500 border-t border-slate-100">
                <div>
                  <span className="font-semibold text-slate-600">Statutory Reference: </span>
                  <span className="font-medium text-slate-800">{rule.rule_reference}</span>
                </div>
                <div>
                  <span className="font-semibold text-slate-600">Validation Type: </span>
                  <span className="font-mono text-slate-800">{rule.validation_type}</span>
                </div>
                <div>
                  <span className="font-semibold text-slate-600">Effective Date: </span>
                  <span className="text-slate-800">{rule.effective_from}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

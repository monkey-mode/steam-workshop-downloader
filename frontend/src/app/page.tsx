"use client";

import { useState, useEffect, useCallback } from "react";
import { Search, ChevronLeft, ChevronRight, SlidersHorizontal } from "lucide-react";
import { browseWorkshop, getItem, WorkshopItem, BrowseResponse } from "@/lib/api";
import WorkshopCard from "@/components/WorkshopCard";
import DownloadPanel from "@/components/DownloadPanel";

const SORT_OPTIONS = [
  { value: "trend", label: "Trending" },
  { value: "top", label: "Top Rated" },
  { value: "new", label: "Newest" },
  { value: "favorites", label: "Most Favorited" },
];

export default function Home() {
  const [appId, setAppId] = useState("255710");
  const [appIdInput, setAppIdInput] = useState("255710");
  const [sort, setSort] = useState("trend");
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [count] = useState(20);

  const [data, setData] = useState<BrowseResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<WorkshopItem[]>([]);

  const totalPages = data ? Math.ceil(data.total / count) : 0;

  const fetchData = useCallback(async () => {
    if (!appId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await browseWorkshop({ app_id: appId, sort, page, count, search });
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch items");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [appId, sort, page, count, search]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSearch = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const raw = searchInput.trim();

    // Detect filedetails URL or bare workshop ID
    const workshopIdMatch = raw.match(/[?&]id=(\d+)/) || (/^\d+$/.test(raw) && raw.length > 6 ? [null, raw] : null);
    if (workshopIdMatch) {
      setLoading(true);
      setError(null);
      try {
        const item = await getItem(workshopIdMatch[1]);
        setData({ total: 1, items: [item], has_api_key: data?.has_api_key ?? false });
        if (item.app_id && item.app_id !== appId) {
          setAppId(item.app_id);
          setAppIdInput(item.app_id);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Item not found");
        setData(null);
      } finally {
        setLoading(false);
      }
      return;
    }

    setSearch(raw);
    setPage(1);
  };

  const handleAppIdSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const raw = appIdInput.trim();
    const match = raw.match(/appid=(\d+)/) || raw.match(/\/app\/(\d+)/);
    setAppId(match ? match[1] : raw);
    setPage(1);
  };

  const toggleSelect = (id: string) => {
    const item = data?.items.find((i) => i.workshop_id === id);
    if (!item) return;
    setSelected((prev) =>
      prev.find((i) => i.workshop_id === id)
        ? prev.filter((i) => i.workshop_id !== id)
        : [...prev, item]
    );
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900 sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 py-3 flex flex-col sm:flex-row items-start sm:items-center gap-3">
          <div className="flex items-center gap-2 shrink-0">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="currentColor">
                <path d="M11.979 0C5.678 0 .511 4.86.022 11.037l6.432 2.658c.545-.371 1.203-.59 1.912-.59.063 0 .125.004.188.006l2.861-4.142V8.91c0-2.495 2.028-4.524 4.524-4.524 2.494 0 4.524 2.031 4.524 4.527s-2.03 4.525-4.524 4.525h-.105l-4.076 2.911c0 .052.004.105.004.159 0 1.875-1.515 3.396-3.39 3.396-1.635 0-3.016-1.173-3.331-2.727L.436 15.27C1.862 20.307 6.486 24 11.979 24c6.627 0 11.999-5.373 11.999-12S18.605 0 11.979 0z"/>
              </svg>
            </div>
            <span className="font-bold text-lg">Workshop Downloader</span>
          </div>

          {/* App ID input */}
          <form onSubmit={handleAppIdSubmit} className="flex gap-2 flex-1 max-w-xs">
            <input
              value={appIdInput}
              onChange={(e) => setAppIdInput(e.target.value)}
              placeholder="App ID or Steam URL"
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500"
            />
            <button
              type="submit"
              className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors"
            >
              Go
            </button>
          </form>

          {/* Search */}
          <form onSubmit={handleSearch} className="flex gap-2 flex-1 max-w-sm">
            <div className="relative flex-1">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search mods..."
                className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-8 pr-3 py-1.5 text-sm focus:outline-none focus:border-blue-500"
              />
            </div>
            <button type="submit" className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm transition-colors">
              Search
            </button>
          </form>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6 pb-32">
        {/* Controls */}
        <div className="flex flex-wrap items-center gap-3 mb-6">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-400">Sort:</span>
            <div className="flex gap-1">
              {SORT_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => { setSort(opt.value); setPage(1); }}
                  className={`px-3 py-1 rounded-lg text-sm transition-colors ${
                    sort === opt.value
                      ? "bg-blue-600 text-white"
                      : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {data && (
            <span className="text-sm text-gray-500 ml-auto">
              {data.total.toLocaleString()} items
              {selected.length > 0 && (
                <span className="ml-2 text-blue-400">{selected.length} selected</span>
              )}
            </span>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-900/30 border border-red-700 rounded-xl p-4 mb-6 text-red-300 text-sm">
            {error}
            <br />
            <span className="text-red-400 text-xs">Make sure the backend is running: <code>python serve.py</code></span>
          </div>
        )}

        {/* Grid */}
        {loading ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {Array.from({ length: 20 }).map((_, i) => (
              <div key={i} className="rounded-xl bg-gray-800 animate-pulse">
                <div className="h-36 bg-gray-700 rounded-t-xl" />
                <div className="p-3 space-y-2">
                  <div className="h-3 bg-gray-700 rounded w-3/4" />
                  <div className="h-3 bg-gray-700 rounded w-1/2" />
                </div>
              </div>
            ))}
          </div>
        ) : data && data.items.length > 0 ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {data.items.map((item) => (
              <WorkshopCard
                key={item.workshop_id}
                item={item}
                selected={!!selected.find((s) => s.workshop_id === item.workshop_id)}
                onToggle={toggleSelect}
              />
            ))}
          </div>
        ) : !loading && !error ? (
          <div className="text-center py-20 text-gray-500">No items found.</div>
        ) : null}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-3 mt-8">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <span className="text-sm text-gray-400">
              Page <span className="text-white font-medium">{page}</span> of{" "}
              <span className="text-white font-medium">{totalPages.toLocaleString()}</span>
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        )}
      </main>

      <DownloadPanel selected={selected} onClear={() => setSelected([])} />
    </div>
  );
}

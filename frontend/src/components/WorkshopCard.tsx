"use client";

import { WorkshopItem } from "@/lib/api";
import { Download, Heart, Users, Tag } from "lucide-react";

interface Props {
  item: WorkshopItem;
  selected: boolean;
  onToggle: (id: string) => void;
}

export default function WorkshopCard({ item, selected, onToggle }: Props) {
  return (
    <div
      onClick={() => onToggle(item.workshop_id)}
      className={`relative cursor-pointer rounded-xl border-2 transition-all duration-150 overflow-hidden bg-gray-800 hover:bg-gray-750 ${
        selected ? "border-blue-500 ring-2 ring-blue-500/30" : "border-gray-700 hover:border-gray-500"
      }`}
    >
      {/* Checkbox overlay */}
      <div className={`absolute top-2 right-2 z-10 w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
        selected ? "bg-blue-500 border-blue-500" : "bg-gray-900/60 border-gray-500"
      }`}>
        {selected && (
          <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
          </svg>
        )}
      </div>

      {/* Preview image */}
      {item.preview_url ? (
        <div className="w-full h-36 overflow-hidden bg-gray-900">
          <img
            src={item.preview_url}
            alt={item.title}
            className="w-full h-full object-cover"
            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
          />
        </div>
      ) : (
        <div className="w-full h-36 bg-gray-900 flex items-center justify-center">
          <span className="text-gray-600 text-sm">No preview</span>
        </div>
      )}

      <div className="p-3">
        <h3 className="font-semibold text-white text-sm line-clamp-2 mb-2 pr-4">{item.title}</h3>

        {/* Tags */}
        {item.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-2">
            {item.tags.slice(0, 3).map((tag) => (
              <span key={tag} className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-gray-700 text-gray-300 text-xs">
                <Tag className="w-2.5 h-2.5" />
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* Stats */}
        <div className="flex items-center gap-3 text-xs text-gray-400">
          <span className="flex items-center gap-1">
            <Users className="w-3 h-3" />
            {item.subscriptions.toLocaleString()}
          </span>
          <span className="flex items-center gap-1">
            <Heart className="w-3 h-3" />
            {item.favorited.toLocaleString()}
          </span>
          <span className="flex items-center gap-1 ml-auto">
            <Download className="w-3 h-3" />
            {item.size_human}
          </span>
        </div>
      </div>
    </div>
  );
}

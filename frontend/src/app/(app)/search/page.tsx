import type { Metadata } from "next";
import { SearchView } from "@/components/search/search-view";

export const metadata: Metadata = { title: "Busca" };

export default function SearchPage() {
  return <SearchView />;
}

"use client";

import Link from "next/link";
import { AuditTrail } from "@/components/audit/AuditTrail";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";

export default function MerchantPage() {
  return (
    <div className="h-screen bg-stone-100 text-slate-900 flex flex-col">
      <header className="border-b border-slate-200 bg-white px-4 py-3 flex items-center gap-4 shadow-sm">
        <Link href="/">
          <Button variant="ghost" size="sm" className="text-slate-500 hover:text-slate-900">
            <ArrowLeft className="h-4 w-4 mr-1" aria-hidden="true" />
            Back
          </Button>
        </Link>
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-lg bg-emerald-600 flex items-center justify-center text-xs font-bold text-white">
            M
          </div>
          <h1 className="font-semibold text-[15px] text-slate-900">Merchant Console</h1>
        </div>
        <span className="ml-auto text-xs text-slate-500">
          All sessions · merchant #1
        </span>
      </header>

      <div className="flex-1 overflow-hidden p-4 md:p-6">
        <div className="mx-auto h-full max-w-3xl rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <AuditTrail merchantId={1} />
        </div>
      </div>
    </div>
  );
}

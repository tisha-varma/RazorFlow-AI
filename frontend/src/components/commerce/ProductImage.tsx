"use client";

import { useState } from "react";
import Image from "next/image";
import { Package } from "lucide-react";

interface ProductImageProps {
  src?: string | null;
  alt: string;
  className?: string;
}

/** Fixed-ratio photo with skeleton while loading and icon fallback on error. */
export function ProductImage({ src, alt, className = "" }: ProductImageProps) {
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);

  return (
    <div className={`relative overflow-hidden bg-slate-100 ${className}`}>
      {!loaded && !failed && (
        <div className="absolute inset-0 animate-pulse bg-slate-200" aria-hidden="true" />
      )}
      {(!src || failed) && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-100" aria-hidden="true">
          <Package className="h-1/4 w-1/4 max-h-8 max-w-8 text-slate-300" />
        </div>
      )}
      {/* unoptimized: catalog art mixes bundled /products files and remote
          DB URLs, which the default optimizer would reject without
          remotePatterns per host. */}
      {src && !failed && (
        <Image
          src={src}
          alt={alt}
          width={400}
          height={300}
          loading="lazy"
          unoptimized
          onLoad={() => setLoaded(true)}
          onError={() => setFailed(true)}
          className={`h-full w-full object-cover transition-opacity duration-300 ${
            loaded ? "opacity-100" : "opacity-0"
          }`}
        />
      )}
    </div>
  );
}

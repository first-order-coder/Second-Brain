const API_BASE = process.env.NEXT_PUBLIC_API_URL;

export function rewriteBackendUrlsToProxy(obj: any) {
  if (!API_BASE) return obj;
  const src = new URL(API_BASE).origin; // e.g., http://backend:8000
  const replacer = (url: string) => {
    // map backend URLs to Next proxies
    // examples:
    //   http://backend:8000/files/ABC  -> /api/files/ABC
    //   http://backend:8000/flashcards/ID -> /api/flashcards/ID
    //   http://backend:8000/summaries/ID -> /api/summaries/ID
    if (url.startsWith(`${src}/files/`)) return url.replace(src, "").replace("/files/", "/api/files/");
    if (url.startsWith(`${src}/flashcards/`)) return url.replace(src, "").replace("/flashcards/", "/api/flashcards/");
    if (url.startsWith(`${src}/summaries/`)) return url.replace(src, "").replace("/summaries/", "/api/summaries/");
    if (url.startsWith(`${src}/upload-pdf`)) return url.replace(src, "").replace("/upload-pdf", "/api/upload/pdf");
    return url;
  };
  const walk = (x: any): any => {
    if (Array.isArray(x)) return x.map(walk);
    if (x && typeof x === "object") {
      const y: any = {};
      for (const [k, v] of Object.entries(x)) {
        if (typeof v === "string") y[k] = v.startsWith("http") ? replacer(v) : v;
        else y[k] = walk(v);
      }
      return y;
    }
    return x;
  };
  return walk(obj);
}

import { getBaseUrl } from "../api/client";

export interface FinalScreenshotProps {
  url: string | null;
}

function resolveUrl(url: string): string {
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  return getBaseUrl() + url;
}

export function FinalScreenshot({ url }: FinalScreenshotProps) {
  const resolvedUrl = url ? resolveUrl(url) : null;
  if (!resolvedUrl) {
    return (
      <div className="space-y-2">
        <h3 className="text-sm font-medium text-slate-700">Final screenshot</h3>
        <div className="flex aspect-video items-center justify-center rounded-input border border-dashed border-border bg-surface-elevated/50 text-sm text-muted-text">
          Not available
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-slate-700">Final screenshot</h3>
      <a
        href={resolvedUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="block overflow-hidden rounded-input border border-border bg-surface shadow-card transition hover:shadow-cardHover"
      >
        <img
          src={resolvedUrl}
          alt="Final run screenshot"
          className="max-h-48 w-full object-contain object-top"
        />
      </a>
      <p className="text-xs text-muted-text">
        Latest terminal capture from the run.
      </p>
      <p className="text-xs text-muted-text">
        <a
          href={resolvedUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary hover:underline"
        >
          Open full size
        </a>
      </p>
    </div>
  );
}

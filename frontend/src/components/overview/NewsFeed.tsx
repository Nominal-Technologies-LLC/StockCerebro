import type { NewsArticle } from '../../types/stock';

interface Props {
  articles: NewsArticle[];
}

export default function NewsFeed({ articles }: Props) {
  if (articles.length === 0) {
    return (
      <div className="card">
        <h3 className="card-header">Recent News</h3>
        <p className="text-sm text-gray-500">No recent news available.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h3 className="card-header">Recent News</h3>
      <div className="space-y-3 max-h-96 overflow-y-auto">
        {articles.map((article, i) => (
          <a
            key={i}
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block p-3 rounded-lg bg-gray-800/50 hover:bg-gray-800 transition-colors"
          >
            <div className="text-sm font-medium text-white line-clamp-2">
              {article.title}
            </div>
            <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
              {article.source && <span>{article.source}</span>}
              {article.published && (
                <>
                  {article.source && <span>-</span>}
                  <span>{formatRelativeTime(article.published)}</span>
                </>
              )}
            </div>
            {article.summary && (
              <p className="text-xs text-gray-400 mt-1 line-clamp-2">{article.summary}</p>
            )}
          </a>
        ))}
      </div>
    </div>
  );
}

function formatRelativeTime(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return dateStr;
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  } catch {
    return dateStr;
  }
}

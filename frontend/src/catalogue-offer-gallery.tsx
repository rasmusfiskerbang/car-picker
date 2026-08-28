import { ChevronLeft, ChevronRight, ImageOff } from "lucide-react";
import { useState } from "react";

import { CatalogueOfferImage } from "@/catalogue-offer-image";

export function CatalogueOfferGallery({
  alt,
  urls,
}: {
  alt: string;
  urls: readonly string[];
}) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [failedUrls, setFailedUrls] = useState<Set<string>>(() => new Set());
  const currentUrl = urls[selectedIndex];
  const currentAvailable = currentUrl !== undefined && !failedUrls.has(currentUrl);

  if (urls.length === 0) {
    return (
      <section aria-label={`Billeder af ${alt}`} className="detail-gallery">
        <CatalogueOfferImage
          alt={alt}
          className="detail-gallery-image"
          urls={[]}
        />
      </section>
    );
  }

  const markFailed = (url: string) => {
    setFailedUrls((current) => {
      if (current.has(url)) return current;
      return new Set(current).add(url);
    });
  };

  const move = (direction: -1 | 1) => {
    setSelectedIndex(
      (selectedIndex + direction + urls.length) % urls.length,
    );
  };

  return (
    <section aria-label={`Billeder af ${alt}`} className="detail-gallery">
      <div className="detail-gallery-main">
        <CatalogueOfferImage
          alt={alt}
          className="detail-gallery-image"
          onImageError={markFailed}
          urls={currentAvailable && currentUrl !== undefined ? [currentUrl] : []}
        />
        {urls.length > 1 && (
          <div className="detail-gallery-controls">
            <button
              aria-label="Forrige billede"
              className="detail-gallery-control"
              type="button"
              onClick={() => move(-1)}
            >
              <ChevronLeft aria-hidden="true" />
            </button>
            <span aria-live="polite" className="detail-gallery-count">
              {selectedIndex + 1} / {urls.length}
            </span>
            <button
              aria-label="Næste billede"
              className="detail-gallery-control"
              type="button"
              onClick={() => move(1)}
            >
              <ChevronRight aria-hidden="true" />
            </button>
          </div>
        )}
      </div>
      {urls.length > 1 && (
        <div className="detail-gallery-thumbnails">
          {urls.map((url, index) => (
            <button
              aria-label={`Vis billede ${index + 1} af ${urls.length}`}
              aria-pressed={selectedIndex === index}
              className={
                selectedIndex === index
                  ? "detail-gallery-thumbnail selected"
                  : "detail-gallery-thumbnail"
              }
              key={url}
              type="button"
              onClick={() => setSelectedIndex(index)}
            >
              {failedUrls.has(url) ? (
                <ImageOff aria-hidden="true" />
              ) : (
                <img
                  alt=""
                  loading="lazy"
                  referrerPolicy="no-referrer"
                  src={url}
                  onError={() => markFailed(url)}
                />
              )}
            </button>
          ))}
        </div>
      )}
      {urls.length > 1 && (
        <p className="detail-gallery-note">
          Billederne følger udbyderens rækkefølge og kan være vejledende. Tjek den
          præcise konfiguration hos udbyderen.
        </p>
      )}
    </section>
  );
}

import { ImageOff } from "lucide-react";
import { useState } from "react";

export function CatalogueOfferImage({
  alt,
  className,
  onImageError,
  urls,
}: {
  alt: string;
  className: string;
  onImageError?: (url: string) => void;
  urls: readonly string[];
}) {
  const [failedUrls, setFailedUrls] = useState<string[]>([]);
  const source = urls.find((url) => !failedUrls.includes(url));

  if (source === undefined) {
    return (
      <div
        aria-label="Billede ikke tilgængeligt"
        className={`${className} catalogue-offer-image-fallback`}
        role="img"
      >
        <ImageOff aria-hidden="true" />
        <span>Billede ikke tilgængeligt</span>
      </div>
    );
  }

  return (
    <div className={className}>
      <img
        alt={alt}
        decoding="async"
        loading="lazy"
        referrerPolicy="no-referrer"
        src={source}
        onError={() =>
          {
            onImageError?.(source);
            setFailedUrls((current) =>
              current.includes(source) ? current : [...current, source],
            );
          }
        }
      />
    </div>
  );
}

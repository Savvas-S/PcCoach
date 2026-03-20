/**
 * SVG icons for PC component categories.
 * Used by BuildLoadingScreen and build result page.
 */

interface CategoryIconProps {
  category: string;
  size?: number;
  className?: string;
}

const CATEGORY_TO_ICON: Record<string, string> = {
  cpu: "cpu",
  motherboard: "board",
  gpu: "gpu",
  ram: "ram",
  storage: "ssd",
  psu: "psu",
  case: "case",
  cooling: "cool",
  monitor: "mon",
  keyboard: "key",
  mouse: "mouse",
  toolkit: "toolkit",
};

export function CategoryIcon({
  category,
  size = 16,
  className = "",
}: CategoryIconProps) {
  const icon = CATEGORY_TO_ICON[category] ?? category;
  const common = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.5,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    className,
  };

  switch (icon) {
    case "cpu":
      return (
        <svg {...common}>
          <rect x="4" y="4" width="16" height="16" rx="2" />
          <rect x="9" y="9" width="6" height="6" />
          <path d="M9 1v3M15 1v3M9 20v3M15 20v3M1 9h3M1 15h3M20 9h3M20 15h3" />
        </svg>
      );
    case "board":
      return (
        <svg {...common}>
          <rect x="2" y="2" width="20" height="20" rx="1" />
          <rect x="6" y="5" width="5" height="4" rx="0.5" />
          <path d="M6 13h12M6 16h8" />
          <circle cx="17" cy="7" r="2" />
        </svg>
      );
    case "gpu":
      return (
        <svg {...common}>
          <rect x="1" y="6" width="22" height="12" rx="2" />
          <path d="M5 6V4M9 6V4M13 6V4" />
          <circle cx="17" cy="12" r="3" />
          <circle cx="8" cy="12" r="2" />
        </svg>
      );
    case "ram":
      return (
        <svg {...common}>
          <rect x="3" y="4" width="18" height="16" rx="1" />
          <path d="M7 4v16M11 4v16M15 4v16M19 4v16" />
          <path d="M9 20v2M15 20v2" />
        </svg>
      );
    case "ssd":
      return (
        <svg {...common}>
          <rect x="2" y="4" width="20" height="16" rx="2" />
          <circle cx="12" cy="12" r="4" />
          <circle cx="12" cy="12" r="1" />
        </svg>
      );
    case "psu":
      return (
        <svg {...common}>
          <rect x="2" y="4" width="20" height="16" rx="2" />
          <circle cx="12" cy="12" r="3" />
          <path d="M12 6v2M12 16v2M6 12h2M16 12h2" />
        </svg>
      );
    case "case":
      return (
        <svg {...common}>
          <rect x="5" y="1" width="14" height="22" rx="2" />
          <circle cx="12" cy="6" r="2" />
          <path d="M9 12h6M9 15h6" />
          <circle cx="12" cy="20" r="1" />
        </svg>
      );
    case "cool":
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="10" />
          <path d="M12 2v4M12 18v4M2 12h4M18 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8" />
        </svg>
      );
    case "mon":
      return (
        <svg {...common}>
          <rect x="2" y="3" width="20" height="14" rx="2" />
          <path d="M8 21h8M12 17v4" />
        </svg>
      );
    case "key":
      return (
        <svg {...common}>
          <rect x="1" y="6" width="22" height="12" rx="2" />
          <path d="M5 10h1M8 10h1M11 10h2M16 10h1M19 10h1M6 14h12" />
        </svg>
      );
    case "mouse":
      return (
        <svg {...common}>
          <rect x="6" y="2" width="12" height="20" rx="6" />
          <path d="M12 2v7M6 9h12" />
        </svg>
      );
    case "toolkit":
      return (
        <svg {...common}>
          <path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z" />
        </svg>
      );
    default:
      return null;
  }
}

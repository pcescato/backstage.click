const SITE_URL = 'https://backstage.click';
const GOOGLE_SITE_VERIFICATION = '';
const BING_SITE_VERIFICATION = '';

export interface SiteConfig {
  name: string;
  description: string;
  url: string;
  ogImage: string;
  author: string;
  email: string;
  locale: string;
  timezone: string;
  phone?: string;
  address?: {
    street: string;
    city: string;
    state: string;
    zip: string;
    country: string;
  };
  socialLinks: string[];
  twitter?: {
    site: string;
    creator: string;
  };
  verification?: {
    google?: string;
    bing?: string;
  };
  /**
   * Branding configuration
   * Logo files: Replace SVGs in src/assets/branding/
   * Favicon: Replace in public/favicon.svg
   */
  branding: {
    /** Logo alt text for accessibility */
    logo: {
      alt: string;
    };
    /** Favicon path (lives in public/) */
    favicon: {
      svg: string;
    };
    /** Theme colors for manifest and browser UI */
    colors: {
      /** Browser toolbar color (hex) */
      themeColor: string;
      /** PWA splash screen background (hex) */
      backgroundColor: string;
    };
  };
}

const siteConfig: SiteConfig = {
  name: 'Backstage',
  description:
    'Audit, migration et optimisation de sites web pour organismes de formation et TPE/PME',
  url: SITE_URL || 'https://backstage.click',
  ogImage: '/og-default.svg',
  author: 'Pascal Cescato',
  email: 'courriel@backstage.click',
  locale: 'fr',
  timezone: 'Europe/Paris',
  socialLinks: [],
  twitter: {
    site: '',
    creator: '',
  },
  verification: {
    google: GOOGLE_SITE_VERIFICATION,
    bing: BING_SITE_VERIFICATION,
  },
  // Branding: Logo files live in src/assets/branding/
  // Replace the SVG files there with your own branding
  branding: {
    logo: {
      alt: 'Backstage',
    },
    favicon: {
      svg: '/favicon.svg',
    },
    colors: {
      themeColor: '#262626',
      backgroundColor: '#ffffff',
    },
  },
};

export default siteConfig;

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
   * Logo and favicon live in public/images/
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
  name: 'Backstage.click',

  description:
    'Conseil informatique indépendant pour TPE et PME : développement web, optimisation WordPress, applications métier, automatisation, audit technique et accompagnement numérique.',

  url: SITE_URL || 'https://backstage.click',

  ogImage: '/og-default.svg',

  author: 'Pascal Cescato',

  email: 'courriel@backstage.click',

  locale: 'fr',

  timezone: 'Europe/Paris',

  organization: {
    name: 'Backstage.click',
    type: 'ProfessionalService',
    founder: 'Pascal Cescato',
    description:
      'Consultant informatique indépendant accompagnant les TPE et PME dans leurs projets web, logiciels métier et transformation numérique.',
    areaServed: [
      'Nouvelle-Aquitaine',
      'France'
    ],
    services: [
      'Développement web',
      'Conseil informatique',
      'Audit technique',
      'Optimisation WordPress',
      'Migration de sites web',
      'Développement d applications métier',
      'Automatisation',
      'Intelligence artificielle'
    ]
  },

  socialLinks: [],

  twitter: {
    site: '',
    creator: '',
  },

  verification: {
    google: GOOGLE_SITE_VERIFICATION,
    bing: BING_SITE_VERIFICATION,
  },

  branding: {
    logo: {
      alt: 'Backstage.click - Conseil informatique et développement web',
    },

    favicon: {
      svg: '/backstage-favicon.webp',
    },

    colors: {
      themeColor: '#262626',
      backgroundColor: '#ffffff',
    },
  },
};

export default siteConfig;

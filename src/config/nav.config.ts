/**
 * Navigation Configuration
 *
 * Defines which pages appear in the site navigation and their display order.
 * Astro handles routing via the filesystem — this only controls nav menus.
 */

export interface NavItem {
  label: string;
  href: string;
  order: number;
  children?: { label: string; href: string }[];
}

export const navItems: NavItem[] = [
  { label: 'Diagnostic', href: '/diagnostic', order: 1 },
  {
    label: 'Prestations',
    href: '/prestations',
    order: 2,
    children: [
      { label: 'CRM & ERP sur-mesure pour PME', href: '/prestations/crm-erp-pme' },
      { label: 'WordPress : maintenance, optimisation et migration', href: '/prestations/wordpress' },
      { label: 'DevOps : déploiement et hébergement', href: '/prestations/devops-deploiement' },
      { label: 'IA & automatisation', href: '/prestations/ia-automatisation' },
    ],
  },
  { label: 'Outils', href: '/outils', order: 3 },
  { label: 'GCF Pro', href: '/gcf-pro', order: 4 },
  { label: 'Contact', href: '/contact', order: 5 },
];

export const footerNavItems: NavItem[] = [...navItems];

export interface LegalLink {
  label: string;
  href: string;
}

export const legalLinks: LegalLink[] = [];

/**
 * Get navigation items sorted by order
 */
export function getNavItems(): NavItem[] {
  return [...navItems].sort((a, b) => a.order - b.order);
}

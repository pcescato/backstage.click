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
}

export const navItems: NavItem[] = [
  { label: 'Diagnostic', href: '/diagnostic', order: 1 },
  { label: 'Prestations', href: '/prestations', order: 2 },
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

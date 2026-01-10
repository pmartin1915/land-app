/**
 * External resource links for property research and deal execution
 * Used by MyFirstDeal page to provide contextual links in each step
 */

export interface ExternalLink {
  label: string
  url: string
  description?: string
}

/**
 * Generate a Google Maps search URL for a county
 */
export function getGoogleMapsUrl(county: string, state: string): string {
  return `https://www.google.com/maps/search/${encodeURIComponent(county)}+county+${state}`
}

/**
 * Generate a Google Maps search URL for a specific property (by parcel ID or coordinates)
 */
export function getGoogleMapsPropertyUrl(county: string, state: string, parcelId?: string): string {
  const searchTerm = parcelId
    ? `${parcelId} ${county} county ${state}`
    : `${county} county ${state}`
  return `https://www.google.com/maps/search/${encodeURIComponent(searchTerm)}`
}

/**
 * FEMA National Flood Hazard Layer Map
 */
export function getFemaFloodMapUrl(): string {
  return 'https://msc.fema.gov/portal/search'
}

/**
 * Get county assessor/GIS website by state
 */
export function getCountyAssessorUrl(state: string): string | null {
  const assessors: Record<string, string> = {
    AR: 'https://www.arcountydata.com/',
    AL: 'https://www.revenue.alabama.gov/property-tax/',
    TX: 'https://comptroller.texas.gov/taxes/property-tax/',
    FL: 'https://floridarevenue.com/property/',
  }
  return assessors[state] || null
}

/**
 * Get state bar association lawyer referral URL
 */
export function getBarAssociationUrl(state: string): string {
  const associations: Record<string, string> = {
    AR: 'https://www.arkbar.com/lawyer-referral',
    AL: 'https://www.alabar.org/lawyer-referral-service/',
    TX: 'https://www.texasbar.com/AM/Template.cfm?Section=Lawyer_Referral_Service',
    FL: 'https://www.floridabar.org/public/lrs/',
  }
  return associations[state] || 'https://www.americanbar.org/groups/lawyer_referral/'
}

/**
 * Get auction platform URL
 */
export function getAuctionPlatformUrl(platform?: string | null): string | null {
  if (!platform) return null

  const platformLower = platform.toLowerCase()

  // Common platforms
  const platforms: Record<string, string> = {
    cosl: 'https://cosl.org/',
    'cosl website': 'https://cosl.org/',
    govease: 'https://www.govease.com/',
    realauction: 'https://www.realauction.com/',
    realtaxdeed: 'https://www.realtaxdeed.com/',
    'grant street': 'https://www.grantstreet.com/',
    'civic source': 'https://www.civicsource.com/',
  }

  // Try exact match first
  for (const [key, url] of Object.entries(platforms)) {
    if (platformLower.includes(key)) {
      return url
    }
  }

  return null
}

/**
 * Land selling platforms
 */
export const landSellingPlatforms = {
  landWatch: 'https://www.landwatch.com/land/for-sale',
  landsOfAmerica: 'https://www.landsofamerica.com/',
  landAndFarm: 'https://www.landandfarm.com/',
  facebookMarketplace: 'https://www.facebook.com/marketplace/category/propertyrentals/',
  craigslist: (state: string) => {
    const stateMap: Record<string, string> = {
      AR: 'littlerock',
      AL: 'birmingham',
      TX: 'dallas',
      FL: 'orlando',
    }
    const city = stateMap[state] || state.toLowerCase()
    return `https://${city}.craigslist.org/search/rea?sale_date=sbyowner`
  },
}

/**
 * Get all due diligence links for a given state
 */
export function getDueDiligenceLinks(state: string = 'AR'): ExternalLink[] {
  const links: ExternalLink[] = [
    {
      label: 'FEMA Flood Maps',
      url: getFemaFloodMapUrl(),
      description: 'Check flood zone risk',
    },
    {
      label: 'Google Maps',
      url: getGoogleMapsUrl('', state),
      description: 'Satellite view and street access',
    },
  ]

  const assessorUrl = getCountyAssessorUrl(state)
  if (assessorUrl) {
    links.push({
      label: 'County GIS/Assessor',
      url: assessorUrl,
      description: 'Verify acreage and lot lines',
    })
  }

  return links
}

/**
 * Get quiet title attorney search links for a state
 */
export function getAttorneyLinks(state: string = 'AR'): ExternalLink[] {
  return [
    {
      label: 'State Bar Lawyer Referral',
      url: getBarAssociationUrl(state),
      description: 'Find licensed attorneys in your state',
    },
    {
      label: 'Avvo - Quiet Title Attorneys',
      url: `https://www.avvo.com/search/lawyer_search?q=quiet+title&loc=${state}`,
      description: 'Attorney reviews and ratings',
    },
  ]
}

/**
 * Get all selling platform links
 */
export function getSellingLinks(state: string = 'AR'): ExternalLink[] {
  return [
    {
      label: 'LandWatch',
      url: landSellingPlatforms.landWatch,
      description: 'Popular land listing site',
    },
    {
      label: 'Lands of America',
      url: landSellingPlatforms.landsOfAmerica,
      description: 'Large land marketplace',
    },
    {
      label: 'Facebook Marketplace',
      url: landSellingPlatforms.facebookMarketplace,
      description: 'Local buyers, no listing fees',
    },
    {
      label: 'Craigslist',
      url: landSellingPlatforms.craigslist(state),
      description: 'Free listings, local reach',
    },
  ]
}

// PropertyMap.tsx - Interactive map with properties using WebGL layers for performance
import React, { useState, useCallback, useMemo, useRef, useEffect } from 'react'
import Map, { Source, Layer, Popup, NavigationControl, ScaleControl, FullscreenControl } from 'react-map-gl'
import type { MapRef, ViewStateChangeEvent, MapLayerMouseEvent, LayerProps } from 'react-map-gl'
import type { FeatureCollection, Feature, Point } from 'geojson'
import { Property } from '../types'
import 'mapbox-gl/dist/mapbox-gl.css'

// Alabama approximate center
const ALABAMA_CENTER = {
  longitude: -86.8287,
  latitude: 32.7794,
  zoom: 6.5
}

// Alabama county centroids for property placement (approximate)
const COUNTY_CENTROIDS: Record<string, { lat: number; lng: number }> = {
  'Autauga': { lat: 32.5346, lng: -86.6467 },
  'Baldwin': { lat: 30.6557, lng: -87.7497 },
  'Barbour': { lat: 31.8704, lng: -85.3935 },
  'Bibb': { lat: 33.0152, lng: -87.1267 },
  'Blount': { lat: 33.9777, lng: -86.5683 },
  'Bullock': { lat: 32.1006, lng: -85.7152 },
  'Butler': { lat: 31.7530, lng: -86.6803 },
  'Calhoun': { lat: 33.7712, lng: -85.8267 },
  'Chambers': { lat: 32.9143, lng: -85.3911 },
  'Cherokee': { lat: 34.1755, lng: -85.6036 },
  'Chilton': { lat: 32.8476, lng: -86.7186 },
  'Choctaw': { lat: 32.0196, lng: -88.2631 },
  'Clarke': { lat: 31.6786, lng: -87.8303 },
  'Clay': { lat: 33.2690, lng: -85.8606 },
  'Cleburne': { lat: 33.6758, lng: -85.5186 },
  'Coffee': { lat: 31.4016, lng: -85.9811 },
  'Colbert': { lat: 34.7012, lng: -87.8058 },
  'Conecuh': { lat: 31.4296, lng: -86.9936 },
  'Coosa': { lat: 32.9363, lng: -86.2467 },
  'Covington': { lat: 31.2485, lng: -86.4514 },
  'Crenshaw': { lat: 31.7313, lng: -86.3133 },
  'Cullman': { lat: 34.1322, lng: -86.8661 },
  'Dale': { lat: 31.4325, lng: -85.6111 },
  'Dallas': { lat: 32.3262, lng: -87.1064 },
  'DeKalb': { lat: 34.4603, lng: -85.8042 },
  'Elmore': { lat: 32.5962, lng: -86.1494 },
  'Escambia': { lat: 31.1246, lng: -87.1614 },
  'Etowah': { lat: 34.0455, lng: -86.0372 },
  'Fayette': { lat: 33.7213, lng: -87.8317 },
  'Franklin': { lat: 34.4426, lng: -87.8433 },
  'Geneva': { lat: 31.0952, lng: -85.8383 },
  'Greene': { lat: 32.8530, lng: -87.9547 },
  'Hale': { lat: 32.7629, lng: -87.6244 },
  'Henry': { lat: 31.5154, lng: -85.2406 },
  'Houston': { lat: 31.1528, lng: -85.2972 },
  'Jackson': { lat: 34.7819, lng: -85.9878 },
  'Jefferson': { lat: 33.5537, lng: -86.8967 },
  'Lamar': { lat: 33.7869, lng: -88.0936 },
  'Lauderdale': { lat: 34.9037, lng: -87.6531 },
  'Lawrence': { lat: 34.5210, lng: -87.3131 },
  'Lee': { lat: 32.6015, lng: -85.3556 },
  'Limestone': { lat: 34.8103, lng: -86.9758 },
  'Lowndes': { lat: 32.1597, lng: -86.6517 },
  'Macon': { lat: 32.3826, lng: -85.6936 },
  'Madison': { lat: 34.7625, lng: -86.5505 },
  'Marengo': { lat: 32.2438, lng: -87.7903 },
  'Marion': { lat: 34.1367, lng: -87.8875 },
  'Marshall': { lat: 34.3665, lng: -86.3064 },
  'Mobile': { lat: 30.6764, lng: -88.1885 },
  'Monroe': { lat: 31.5298, lng: -87.3686 },
  'Montgomery': { lat: 32.2269, lng: -86.1728 },
  'Morgan': { lat: 34.4531, lng: -86.8486 },
  'Perry': { lat: 32.6371, lng: -87.2939 },
  'Pickens': { lat: 33.2821, lng: -88.0897 },
  'Pike': { lat: 31.8021, lng: -85.9439 },
  'Randolph': { lat: 33.2927, lng: -85.4589 },
  'Russell': { lat: 32.2885, lng: -85.1842 },
  'Saint Clair': { lat: 33.7136, lng: -86.3153 },
  'Shelby': { lat: 33.2639, lng: -86.6608 },
  'Sumter': { lat: 32.5936, lng: -88.1992 },
  'Talladega': { lat: 33.4008, lng: -86.1656 },
  'Tallapoosa': { lat: 32.8636, lng: -85.7964 },
  'Tuscaloosa': { lat: 33.2896, lng: -87.5251 },
  'Walker': { lat: 33.8034, lng: -87.2967 },
  'Washington': { lat: 31.4113, lng: -88.2078 },
  'Wilcox': { lat: 31.9896, lng: -87.3094 },
  'Winston': { lat: 34.1493, lng: -87.3758 },
}

// Seeded random for consistent jitter
function seededRandom(seed: string): number {
  let hash = 0
  for (let i = 0; i < seed.length; i++) {
    const char = seed.charCodeAt(i)
    hash = ((hash << 5) - hash) + char
    hash = hash & hash
  }
  return (Math.abs(hash) % 10000) / 10000
}

// Get approximate coordinates for a property based on county
function getPropertyCoordinates(property: Property): { lat: number; lng: number } | null {
  if (!property.county) return null

  const countyName = property.county.trim()
  const centroid = COUNTY_CENTROIDS[countyName]

  if (!centroid) return null

  // Use property ID as seed for consistent jitter
  const seed = property.id || property.parcel_id
  const jitterLat = (seededRandom(seed + 'lat') - 0.5) * 0.15
  const jitterLng = (seededRandom(seed + 'lng') - 0.5) * 0.15

  return {
    lat: centroid.lat + jitterLat,
    lng: centroid.lng + jitterLng
  }
}

// Property info for popup
interface PropertyPopupInfo {
  id: string
  county: string
  amount: number
  acreage?: number
  price_per_acre?: number
  investment_score?: number
  water_score: number
  coordinates: [number, number]
}

// Layer styles - defined outside component to prevent recreation
const clusterLayer: LayerProps = {
  id: 'clusters',
  type: 'circle',
  filter: ['has', 'point_count'],
  paint: {
    'circle-color': [
      'step',
      ['get', 'point_count'],
      '#3B82F6', // blue for small clusters
      10, '#10B981', // green for medium
      50, '#F59E0B', // amber for large
      100, '#EF4444' // red for very large
    ],
    'circle-radius': [
      'step',
      ['get', 'point_count'],
      20, // default
      10, 25,
      50, 30,
      100, 40
    ],
    'circle-stroke-width': 2,
    'circle-stroke-color': '#fff'
  }
}

const clusterCountLayer: LayerProps = {
  id: 'cluster-count',
  type: 'symbol',
  filter: ['has', 'point_count'],
  layout: {
    'text-field': '{point_count_abbreviated}',
    'text-font': ['DIN Offc Pro Medium', 'Arial Unicode MS Bold'],
    'text-size': 12
  },
  paint: {
    'text-color': '#fff'
  }
}

// Unclustered point layer with data-driven styling based on investment score
const unclusteredPointLayer: LayerProps = {
  id: 'unclustered-point',
  type: 'circle',
  filter: ['!', ['has', 'point_count']],
  paint: {
    'circle-color': [
      'case',
      ['>=', ['get', 'investment_score'], 85], '#10B981', // green - elite
      ['>=', ['get', 'investment_score'], 70], '#3B82F6', // blue - good
      ['>=', ['get', 'investment_score'], 50], '#F59E0B', // amber - moderate
      '#EF4444' // red - low
    ],
    'circle-radius': 8,
    'circle-stroke-width': 2,
    'circle-stroke-color': '#fff'
  }
}

interface PropertyMapProps {
  properties: Property[]
  selectedProperty?: Property | null
  onPropertySelect?: (property: Property | null) => void
  showFloodZones?: boolean
  showClusters?: boolean
  className?: string
}

export function PropertyMap({
  properties,
  selectedProperty,
  onPropertySelect,
  showFloodZones = false,
  showClusters = true,
  className = ''
}: PropertyMapProps) {
  const mapRef = useRef<MapRef>(null)
  const [viewState, setViewState] = useState(ALABAMA_CENTER)
  const [popupInfo, setPopupInfo] = useState<PropertyPopupInfo | null>(null)
  const [cursor, setCursor] = useState<string>('grab')

  // Mapbox token from environment
  const mapboxToken = import.meta.env.VITE_MAPBOX_TOKEN || ''

  // Convert properties to GeoJSON - only recalculate when properties change
  const geojson: FeatureCollection = useMemo(() => {
    const features: Feature<Point>[] = properties
      .map((property): Feature<Point> | null => {
        const coords = getPropertyCoordinates(property)
        if (!coords) return null

        return {
          type: 'Feature',
          properties: {
            id: property.id,
            parcel_id: property.parcel_id,
            county: property.county || 'Unknown',
            amount: property.amount,
            acreage: property.acreage,
            price_per_acre: property.price_per_acre,
            investment_score: property.investment_score || 0,
            water_score: property.water_score || 0,
          },
          geometry: {
            type: 'Point',
            coordinates: [coords.lng, coords.lat]
          }
        }
      })
      .filter((f): f is Feature<Point> => f !== null)

    return {
      type: 'FeatureCollection',
      features
    }
  }, [properties])

  // Handle map movement
  const onMove = useCallback((evt: ViewStateChangeEvent) => {
    setViewState(evt.viewState)
  }, [])

  // Handle click on map layer
  const onClick = useCallback((event: MapLayerMouseEvent) => {
    const feature = event.features?.[0]
    if (!feature) {
      setPopupInfo(null)
      onPropertySelect?.(null)
      return
    }

    const props = feature.properties
    if (!props) return

    // Check if it's a cluster
    if (props.cluster) {
      // Zoom into cluster
      const clusterId = props.cluster_id
      const mapboxSource = mapRef.current?.getSource('properties-source')

      if (mapboxSource && 'getClusterExpansionZoom' in mapboxSource) {
        (mapboxSource as any).getClusterExpansionZoom(clusterId, (err: any, zoom: number) => {
          if (err) return

          const geometry = feature.geometry as Point
          mapRef.current?.easeTo({
            center: geometry.coordinates as [number, number],
            zoom: Math.min(zoom, 14),
            duration: 500
          })
        })
      }
      return
    }

    // Single property click
    const geometry = feature.geometry as Point
    const coordinates = geometry.coordinates as [number, number]

    setPopupInfo({
      id: props.id,
      county: props.county,
      amount: props.amount,
      acreage: props.acreage,
      price_per_acre: props.price_per_acre,
      investment_score: props.investment_score,
      water_score: props.water_score,
      coordinates
    })

    // Find and select the full property object
    const fullProperty = properties.find(p => p.id === props.id)
    if (fullProperty) {
      onPropertySelect?.(fullProperty)
    }
  }, [properties, onPropertySelect])

  // Handle mouse enter/leave for cursor
  const onMouseEnter = useCallback(() => {
    setCursor('pointer')
  }, [])

  const onMouseLeave = useCallback(() => {
    setCursor('grab')
  }, [])

  // Format price
  const formatPrice = (amount: number): string => {
    if (amount >= 1000) {
      return `$${(amount / 1000).toFixed(1)}k`
    }
    return `$${amount.toLocaleString()}`
  }

  // Get investment score color
  const getScoreColor = (score: number | undefined): string => {
    if (!score) return '#6B7280'
    if (score >= 85) return '#10B981'
    if (score >= 70) return '#3B82F6'
    if (score >= 50) return '#F59E0B'
    return '#EF4444'
  }

  if (!mapboxToken) {
    return (
      <div className={`flex items-center justify-center bg-surface rounded-lg border border-neutral-1 ${className}`}>
        <div className="text-center p-8">
          <h3 className="text-lg font-semibold text-text-primary mb-2">Mapbox Token Required</h3>
          <p className="text-text-muted mb-4">
            To display the map, add your Mapbox access token to the environment:
          </p>
          <code className="block bg-card p-3 rounded text-sm text-text-primary">
            VITE_MAPBOX_TOKEN=your_token_here
          </code>
          <p className="text-text-muted mt-4 text-sm">
            Get a free token at{' '}
            <a
              href="https://account.mapbox.com/access-tokens/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-accent-primary hover:underline"
            >
              mapbox.com
            </a>
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className={`relative ${className}`}>
      <Map
        ref={mapRef}
        {...viewState}
        onMove={onMove}
        onClick={onClick}
        onMouseEnter={onMouseEnter}
        onMouseLeave={onMouseLeave}
        style={{ width: '100%', height: '100%' }}
        mapStyle="mapbox://styles/mapbox/outdoors-v12"
        mapboxAccessToken={mapboxToken}
        attributionControl={false}
        cursor={cursor}
        interactiveLayerIds={['clusters', 'unclustered-point']}
      >
        {/* Navigation Controls */}
        <NavigationControl position="top-right" />
        <ScaleControl position="bottom-left" />
        <FullscreenControl position="top-right" />

        {/* Properties GeoJSON Source with built-in clustering */}
        <Source
          id="properties-source"
          type="geojson"
          data={geojson}
          cluster={showClusters}
          clusterMaxZoom={14}
          clusterRadius={50}
        >
          {/* Cluster circles */}
          <Layer {...clusterLayer} />
          {/* Cluster count labels */}
          <Layer {...clusterCountLayer} />
          {/* Individual property points */}
          <Layer {...unclusteredPointLayer} />
        </Source>

        {/* Property Popup */}
        {popupInfo && (
          <Popup
            longitude={popupInfo.coordinates[0]}
            latitude={popupInfo.coordinates[1]}
            anchor="bottom"
            onClose={() => {
              setPopupInfo(null)
              onPropertySelect?.(null)
            }}
            closeOnClick={false}
            className="property-popup"
          >
            <div className="p-2 min-w-[200px]">
              <div className="font-semibold text-gray-900 mb-1">
                {popupInfo.county} County
              </div>
              <div className="text-sm text-gray-600 space-y-1">
                <div className="flex justify-between">
                  <span>Price:</span>
                  <span className="font-medium">{formatPrice(popupInfo.amount)}</span>
                </div>
                {popupInfo.acreage && (
                  <div className="flex justify-between">
                    <span>Acreage:</span>
                    <span className="font-medium">{popupInfo.acreage.toFixed(2)} ac</span>
                  </div>
                )}
                {popupInfo.price_per_acre && (
                  <div className="flex justify-between">
                    <span>$/Acre:</span>
                    <span className="font-medium">${popupInfo.price_per_acre.toLocaleString()}</span>
                  </div>
                )}
                {popupInfo.investment_score && (
                  <div className="flex justify-between">
                    <span>Score:</span>
                    <span
                      className="font-bold"
                      style={{ color: getScoreColor(popupInfo.investment_score) }}
                    >
                      {popupInfo.investment_score.toFixed(1)}
                    </span>
                  </div>
                )}
                {popupInfo.water_score > 0 && (
                  <div className="flex justify-between">
                    <span>Water:</span>
                    <span className="font-medium text-blue-600">
                      +{popupInfo.water_score.toFixed(0)} pts
                    </span>
                  </div>
                )}
              </div>
              <div className="mt-2 pt-2 border-t border-gray-200">
                <button
                  className="w-full px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
                  onClick={() => {
                    const fullProperty = properties.find(p => p.id === popupInfo.id)
                    if (fullProperty) {
                      onPropertySelect?.(fullProperty)
                    }
                  }}
                >
                  View Details
                </button>
              </div>
            </div>
          </Popup>
        )}
      </Map>

      {/* Map Legend */}
      <div className="absolute bottom-8 right-4 bg-card rounded-lg shadow-lg border border-neutral-1 p-3">
        <div className="text-xs font-semibold text-text-primary mb-2">Investment Score</div>
        <div className="space-y-1 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#10B981' }} />
            <span className="text-text-muted">Elite (85+)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#3B82F6' }} />
            <span className="text-text-muted">Good (70-84)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#F59E0B' }} />
            <span className="text-text-muted">Moderate (50-69)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#EF4444' }} />
            <span className="text-text-muted">Low (&lt;50)</span>
          </div>
        </div>
      </div>

      {/* Property Count */}
      <div className="absolute top-4 right-16 bg-card rounded-lg shadow-lg border border-neutral-1 px-3 py-1">
        <span className="text-xs text-text-muted">
          {properties.length.toLocaleString()} properties
        </span>
      </div>
    </div>
  )
}

export default PropertyMap

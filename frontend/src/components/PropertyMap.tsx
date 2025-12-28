// PropertyMap.tsx - Interactive map with properties and FEMA flood zone overlay
import React, { useState, useCallback, useMemo, useRef, useEffect } from 'react'
import Map, { Source, Layer, Marker, Popup, NavigationControl, ScaleControl, FullscreenControl } from 'react-map-gl'
import Supercluster from 'supercluster'
import type { MapRef, ViewStateChangeEvent, MapLayerMouseEvent } from 'react-map-gl'
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

// Get approximate coordinates for a property based on county
function getPropertyCoordinates(property: Property): { lat: number; lng: number } | null {
  if (!property.county) return null

  const countyName = property.county.trim()
  const centroid = COUNTY_CENTROIDS[countyName]

  if (!centroid) return null

  // Add some random jitter within the county for visual separation
  const jitterLat = (Math.random() - 0.5) * 0.15
  const jitterLng = (Math.random() - 0.5) * 0.15

  return {
    lat: centroid.lat + jitterLat,
    lng: centroid.lng + jitterLng
  }
}

// Cluster point type
interface ClusterPoint {
  type: 'Feature'
  properties: {
    cluster?: boolean
    cluster_id?: number
    point_count?: number
    point_count_abbreviated?: string
    property?: Property
  }
  geometry: {
    type: 'Point'
    coordinates: [number, number]
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
  showFloodZones = true,
  showClusters = true,
  className = ''
}: PropertyMapProps) {
  const mapRef = useRef<MapRef>(null)
  const [viewState, setViewState] = useState(ALABAMA_CENTER)
  const [popupInfo, setPopupInfo] = useState<Property | null>(null)
  const [clusters, setClusters] = useState<ClusterPoint[]>([])

  // Mapbox token from environment
  const mapboxToken = import.meta.env.VITE_MAPBOX_TOKEN || ''

  // Initialize supercluster
  const supercluster = useMemo(() => {
    const sc = new Supercluster({
      radius: 60,
      maxZoom: 14,
      minZoom: 0,
    })
    return sc
  }, [])

  // Convert properties to GeoJSON points
  const points = useMemo<ClusterPoint[]>(() => {
    return properties
      .map((property): ClusterPoint | null => {
        const coords = getPropertyCoordinates(property)
        if (!coords) return null

        return {
          type: 'Feature',
          properties: {
            property,
          },
          geometry: {
            type: 'Point',
            coordinates: [coords.lng, coords.lat],
          },
        }
      })
      .filter((p): p is ClusterPoint => p !== null)
  }, [properties])

  // Load points into supercluster and get clusters for current view
  useEffect(() => {
    if (!showClusters || points.length === 0) {
      setClusters(points)
      return
    }

    supercluster.load(points)

    const bounds = mapRef.current?.getMap().getBounds()
    if (bounds) {
      const clusterData = supercluster.getClusters(
        [bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()],
        Math.floor(viewState.zoom)
      ) as ClusterPoint[]
      setClusters(clusterData)
    }
  }, [points, viewState.zoom, showClusters, supercluster])

  // Handle map movement
  const onMove = useCallback((evt: ViewStateChangeEvent) => {
    setViewState(evt.viewState)
  }, [])

  // Handle cluster click - zoom into cluster
  const handleClusterClick = useCallback((clusterId: number, coordinates: [number, number]) => {
    const expansionZoom = Math.min(supercluster.getClusterExpansionZoom(clusterId), 14)

    mapRef.current?.flyTo({
      center: coordinates,
      zoom: expansionZoom,
      duration: 500
    })
  }, [supercluster])

  // Get investment score color
  const getScoreColor = (score: number | undefined): string => {
    if (!score) return '#6B7280' // gray
    if (score >= 85) return '#10B981' // green - elite
    if (score >= 70) return '#3B82F6' // blue - good
    if (score >= 50) return '#F59E0B' // yellow - moderate
    return '#EF4444' // red - low
  }

  // Format price
  const formatPrice = (amount: number): string => {
    if (amount >= 1000) {
      return `$${(amount / 1000).toFixed(1)}k`
    }
    return `$${amount.toLocaleString()}`
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
        style={{ width: '100%', height: '100%' }}
        mapStyle="mapbox://styles/mapbox/outdoors-v12"
        mapboxAccessToken={mapboxToken}
        attributionControl={false}
      >
        {/* Navigation Controls */}
        <NavigationControl position="top-right" />
        <ScaleControl position="bottom-left" />
        <FullscreenControl position="top-right" />

        {/* FEMA Flood Hazard Layer */}
        {showFloodZones && (
          <Source
            id="fema-flood-zones"
            type="raster"
            tiles={[
              'https://hazards.fema.gov/gis/nfhl/rest/services/public/NFHL/MapServer/export?dpi=96&transparent=true&format=png24&bbox={bbox-epsg-3857}&bboxSR=3857&imageSR=3857&size=256,256&f=image'
            ]}
            tileSize={256}
          >
            <Layer
              id="fema-flood-layer"
              type="raster"
              paint={{
                'raster-opacity': 0.5
              }}
            />
          </Source>
        )}

        {/* Property Clusters and Markers */}
        {clusters.map((cluster) => {
          const [longitude, latitude] = cluster.geometry.coordinates
          const { cluster: isCluster, point_count: pointCount, property } = cluster.properties

          // Render cluster
          if (isCluster && cluster.properties.cluster_id !== undefined) {
            return (
              <Marker
                key={`cluster-${cluster.properties.cluster_id}`}
                longitude={longitude}
                latitude={latitude}
                anchor="center"
                onClick={(e) => {
                  e.originalEvent.stopPropagation()
                  handleClusterClick(cluster.properties.cluster_id!, [longitude, latitude])
                }}
              >
                <div
                  className="flex items-center justify-center rounded-full bg-accent-primary text-white font-bold cursor-pointer shadow-lg border-2 border-white transition-transform hover:scale-110"
                  style={{
                    width: `${Math.min(50 + (pointCount || 0) / 5, 80)}px`,
                    height: `${Math.min(50 + (pointCount || 0) / 5, 80)}px`,
                  }}
                >
                  {pointCount}
                </div>
              </Marker>
            )
          }

          // Render individual property marker
          if (property) {
            const isSelected = selectedProperty?.id === property.id
            return (
              <Marker
                key={`property-${property.id}`}
                longitude={longitude}
                latitude={latitude}
                anchor="bottom"
                onClick={(e) => {
                  e.originalEvent.stopPropagation()
                  setPopupInfo(property)
                  onPropertySelect?.(property)
                }}
              >
                <div
                  className={`cursor-pointer transition-transform ${isSelected ? 'scale-125' : 'hover:scale-110'}`}
                  title={`${property.county}: ${formatPrice(property.amount)}`}
                >
                  <svg
                    width="24"
                    height="36"
                    viewBox="0 0 24 36"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      d="M12 0C5.383 0 0 5.383 0 12c0 9 12 24 12 24s12-15 12-24c0-6.617-5.383-12-12-12z"
                      fill={getScoreColor(property.investment_score)}
                      stroke={isSelected ? '#FFFFFF' : 'none'}
                      strokeWidth={isSelected ? 2 : 0}
                    />
                    <circle cx="12" cy="12" r="5" fill="white" />
                  </svg>
                </div>
              </Marker>
            )
          }

          return null
        })}

        {/* Property Popup */}
        {popupInfo && (
          <Popup
            longitude={getPropertyCoordinates(popupInfo)?.lng || 0}
            latitude={getPropertyCoordinates(popupInfo)?.lat || 0}
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
                  onClick={() => onPropertySelect?.(popupInfo)}
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
        {showFloodZones && (
          <>
            <div className="border-t border-neutral-1 my-2" />
            <div className="text-xs font-semibold text-text-primary mb-1">FEMA Flood Zones</div>
            <div className="text-xs text-text-muted">Blue shaded areas indicate flood risk</div>
          </>
        )}
      </div>

      {/* Map Controls */}
      <div className="absolute top-4 left-4 bg-card rounded-lg shadow-lg border border-neutral-1 p-2">
        <div className="flex flex-col gap-2">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showFloodZones}
              onChange={() => {}}
              className="rounded border-neutral-2 text-accent-primary focus:ring-accent-primary"
              disabled
            />
            <span className="text-xs text-text-primary">FEMA Flood Zones</span>
          </label>
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

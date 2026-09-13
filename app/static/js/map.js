/**
 * ERA5-Land Web GIS - Map Management Module (Leaflet)
 * Handles Leaflet initialization, layer management (raster image overlays,
 * wind vector arrows, administrative boundaries), map interactions, and polygon drawing.
 */

const MapModule = (() => {
    let map = null;
    let currentRasterLayer = null;
    let windLayerGroup = null;
    let boundaryLayerGroup = null;
    let clickMarker = null;

    // Basemap tile layers
    const baseLayers = {
        osm: L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap | &copy; Fajri Rinaldi Chan',
            maxZoom: 18
        }),
        satellite: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles &copy; Esri | &copy; Fajri Rinaldi Chan',
            maxZoom: 18
        })
    };

    // Default map center (West Sumatra / Central Sumatra)
    const DEFAULT_CENTER = [-0.5, 100.5];
    const DEFAULT_ZOOM = 7;

    /**
     * Initialize Leaflet map instance
     */
    function init() {
        map = L.map('map', {
            center: DEFAULT_CENTER,
            zoom: DEFAULT_ZOOM,
            minZoom: 5,
            maxZoom: 14,
            zoomControl: false,
            layers: [baseLayers.osm]
        });

        // Add zoom control at top-left
        L.control.zoom({ position: 'topleft' }).addTo(map);

        // Customize attribution prefix with copyright
        if (map.attributionControl) {
            map.attributionControl.setPrefix('<a href="https://leafletjs.com" target="_blank">Leaflet</a> &bull; &copy; Fajri Rinaldi Chan');
        }

        // Layer groups
        windLayerGroup = L.layerGroup().addTo(map);
        boundaryLayerGroup = L.layerGroup().addTo(map);

        // Mouse hover coordinate tracker
        map.on('mousemove', (e) => {
            const coordEl = document.getElementById('coordText');
            if (coordEl) {
                coordEl.innerHTML = `Lat: <strong>${e.latlng.lat.toFixed(3)}°</strong>, Lon: <strong>${e.latlng.lng.toFixed(3)}°</strong> | Zoom: <strong>${map.getZoom()}</strong>`;
            }
        });

        // Map click handler for point time-series query
        map.on('click', (e) => {
            handleMapClick(e.latlng.lat, e.latlng.lng);
        });

        // Load administrative boundaries
        loadBoundaries();

        return map;
    }

    /**
     * Switch basemap layer
     */
    function setBasemap(type) {
        Object.values(baseLayers).forEach(layer => {
            if (map.hasLayer(layer)) {
                map.removeLayer(layer);
            }
        });
        if (baseLayers[type]) {
            map.addLayer(baseLayers[type]);
            baseLayers[type].bringToBack();
        }
    }


    /**
     * Update ERA5-Land raster overlay
     */
    async function updateRaster(params) {
        const loading = document.getElementById('mapLoading');
        if (loading) loading.classList.add('active');

        try {
            const query = new URLSearchParams({
                variable: params.variable,
                aggregation: params.aggregation || 'hourly',
                smooth: params.smooth ? 'true' : 'false'
            });

            if (params.aggregation === 'hourly' && params.time) {
                query.append('time', params.time);
            } else if (params.date) {
                query.append('date', params.date);
            }

            const res = await fetch(`/api/map?${query.toString()}`);
            if (!res.ok) throw new Error(`API error ${res.status}`);
            const data = await res.json();

            // Replace existing image overlay
            if (currentRasterLayer) {
                map.removeLayer(currentRasterLayer);
                currentRasterLayer = null;
            }

            const isRasterVisible = document.getElementById('layerRasterCheck')?.checked ?? true;

            if (isRasterVisible && data.image_url && data.bounds) {
                const opacity = parseFloat(document.getElementById('opacityRange')?.value || 80) / 100;
                currentRasterLayer = L.imageOverlay(data.image_url, data.bounds, {
                    opacity: opacity,
                    interactive: false,
                    crossOrigin: true
                });
                currentRasterLayer.addTo(map);
                currentRasterLayer.bringToBack();
                // Ensure basemap stays strictly behind
                Object.values(baseLayers).forEach(bl => {
                    if (map.hasLayer(bl)) bl.bringToBack();
                });
            }

            // Update Map Legend
            if (data.legend) {
                updateLegend(data.legend);
            }

            // Update badge in navbar
            const varBadge = document.getElementById('activeVariableBadge');
            const timeBadge = document.getElementById('activeTimeBadge');
            if (varBadge) varBadge.textContent = `${data.name} (${data.unit})`;
            if (timeBadge) timeBadge.textContent = data.time ? data.time.replace('T', ' ') : params.date || '';

            return data;
        } catch (err) {
            console.error('Failed to load raster overlay:', err);
        } finally {
            if (loading) loading.classList.remove('active');
        }
    }

    /**
     * Update Map Legend UI
     */
    function updateLegend(legend) {
        const titleEl = document.getElementById('legendTitle');
        const unitEl = document.getElementById('legendUnit');
        const barEl = document.getElementById('legendBar');
        const ticksEl = document.getElementById('legendTicks');

        if (titleEl) titleEl.textContent = legend.name || legend.variable;
        if (unitEl) unitEl.textContent = `(${legend.unit || ''})`;

        // Build CSS linear gradient stops
        if (legend.gradient && barEl) {
            const stops = legend.gradient.map(s => `${s.color} ${s.position}%`).join(', ');
            barEl.style.background = `linear-gradient(to right, ${stops})`;
        }

        // Build ticks
        if (legend.ticks && ticksEl) {
            ticksEl.innerHTML = '';
            legend.ticks.forEach(t => {
                const span = document.createElement('span');
                span.textContent = t;
                ticksEl.appendChild(span);
            });
        }
    }

    /**
     * Update Wind Vector Arrows Overlay
     */
    async function updateWind(timeStr) {
        const isWindChecked = document.getElementById('layerWindCheck')?.checked;
        windLayerGroup.clearLayers();
        if (!isWindChecked) return;

        try {
            const query = new URLSearchParams({ stride: '3' });
            if (timeStr) query.append('time', timeStr);

            const res = await fetch(`/api/wind?${query.toString()}`);
            if (!res.ok) return;
            const data = await res.json();

            data.vectors.forEach(v => {
                // Direction v.direction in degrees (direction from which the wind blows)
                // Flow arrow points in direction + 180
                const arrowRotation = (v.direction + 180) % 360;
                // Scale arrow size and color by speed
                const speed = v.speed;
                const color = speed > 6 ? '#f43f5e' : speed > 3 ? '#38bdf8' : '#a7f3d0';

                const arrowHtml = `
                    <div style="
                        transform: rotate(${arrowRotation}deg);
                        width: 24px;
                        height: 24px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        color: ${color};
                        font-size: 16px;
                        filter: drop-shadow(0 0 2px rgba(0,0,0,0.8));
                    ">
                        <i class="fa-solid fa-arrow-up"></i>
                    </div>
                `;

                const icon = L.divIcon({
                    html: arrowHtml,
                    className: 'wind-arrow-icon',
                    iconSize: [24, 24],
                    iconAnchor: [12, 12]
                });

                const marker = L.marker([v.lat, v.lon], { icon: icon });
                marker.bindTooltip(`Kecepatan: <strong>${v.speed} m/s</strong><br>Arah: <strong>${v.direction}°</strong>`, {
                    direction: 'top',
                    offset: [0, -10]
                });
                windLayerGroup.addLayer(marker);
            });
        } catch (err) {
            console.error('Failed to update wind vectors:', err);
        }
    }

    /**
     * Load Administrative Boundaries GeoJSON
     */
    async function loadBoundaries() {
        try {
            const res = await fetch('/api/regions');
            if (!res.ok) return;
            const geojson = await res.json();

            boundaryLayerGroup.clearLayers();
            const geoLayer = L.geoJSON(geojson, {
                style: {
                    color: '#38bdf8',
                    weight: 1.5,
                    dashArray: '4, 4',
                    fillColor: 'transparent',
                    fillOpacity: 0
                },
                onEachFeature: (feature, layer) => {
                    if (feature.properties && feature.properties.name) {
                        layer.bindTooltip(`<strong>${feature.properties.name}</strong>`, {
                            sticky: true,
                            className: 'boundary-tooltip'
                        });
                    }
                }
            });

            boundaryLayerGroup.addLayer(geoLayer);
        } catch (err) {
            console.warn('Could not load administrative boundaries:', err);
        }
    }

    /**
     * Handle click on map: place marker, open popup, trigger dashboard time series
     */
    function handleMapClick(lat, lon) {
        if (clickMarker) {
            map.removeLayer(clickMarker);
        }

        const customPinIcon = L.divIcon({
            html: `
                <div style="
                    background: linear-gradient(135deg, #0284c7, #06b6d4);
                    width: 28px;
                    height: 28px;
                    border-radius: 50% 50% 50% 0;
                    transform: rotate(-45deg);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border: 2px solid #ffffff;
                    box-shadow: 0 4px 10px rgba(0,0,0,0.5);
                ">
                    <i class="fa-solid fa-crosshairs" style="transform: rotate(45deg); color: #fff; font-size: 12px;"></i>
                </div>
            `,
            className: 'custom-click-pin',
            iconSize: [28, 28],
            iconAnchor: [7, 28],
            popupAnchor: [7, -24]
        });

        clickMarker = L.marker([lat, lon], { icon: customPinIcon }).addTo(map);

        clickMarker.bindPopup(`
            <div class="popup-card">
                <div class="popup-title">Titik Terpilih</div>
                <div class="popup-coords">Lat: ${lat.toFixed(3)}°, Lon: ${lon.toFixed(3)}°</div>
                <div class="popup-val-row">
                    <span>Sedang memuat data...</span>
                </div>
            </div>
        `, { className: 'custom-leaflet-popup' }).openPopup();

        // Notify Dashboard to extract and display time series
        if (window.Dashboard && window.Dashboard.loadPointTimeSeries) {
            window.Dashboard.loadPointTimeSeries(lat, lon, clickMarker);
        }
    }

    /**
     * Set raster opacity
     */
    function setOpacity(value) {
        if (currentRasterLayer) {
            currentRasterLayer.setOpacity(value);
        }
    }

    /**
     * Toggle raster layer visibility
     */
    function toggleRaster(visible) {
        if (!currentRasterLayer) return;
        if (visible) {
            map.addLayer(currentRasterLayer);
        } else {
            map.removeLayer(currentRasterLayer);
        }
    }

    /**
     * Toggle wind layer visibility
     */
    function toggleWind(visible) {
        if (visible) {
            map.addLayer(windLayerGroup);
        } else {
            map.removeLayer(windLayerGroup);
        }
    }

    /**
     * Toggle boundary layer visibility
     */
    function toggleBoundary(visible) {
        if (visible) {
            map.addLayer(boundaryLayerGroup);
        } else {
            map.removeLayer(boundaryLayerGroup);
        }
    }

    /**
     * Reset map view to center
     */
    function resetView() {
        map.setView(DEFAULT_CENTER, DEFAULT_ZOOM, { animate: true });
    }

    return {
        init,
        updateRaster,
        updateWind,
        setOpacity,
        toggleRaster,
        toggleWind,
        toggleBoundary,
        setBasemap,
        resetView,
        getMap: () => map
    };
})();

/**
 * ERA5-Land Web GIS - Dashboard & Analytics Module
 * Handles filter controls, ECharts time series visualizations,
 * spatial polygon analysis, animation player, and CSV downloads.
 */

const Dashboard = (() => {
    let chartInstance = null;
    let currentPoint = null; // { lat, lon, marker }
    let isPlaying = false;
    let playInterval = null;
    let availableTimes = [];

    /**
     * Initialize dashboard components and event listeners
     */
    function init() {
        // Initialize Leaflet Map
        MapModule.init();

        // Initialize ECharts container
        initChart();

        // Bind DOM event listeners
        bindEvents();

        // Load initial time steps
        loadInitialTimes();

        // Trigger initial map render
        applyFilters();
    }

    /**
     * Initialize ECharts instance
     */
    function initChart() {
        const chartDom = document.getElementById('timeseriesChart');
        if (!chartDom) return;

        chartInstance = echarts.init(chartDom, 'dark', {
            renderer: 'canvas'
        });

        // Set default empty chart state
        chartInstance.setOption({
            backgroundColor: 'transparent',
            textStyle: { fontFamily: 'Inter, sans-serif' },
            grid: {
                top: 30,
                bottom: 50,
                left: 60,
                right: 30
            },
            xAxis: {
                type: 'category',
                data: [],
                axisLine: { lineStyle: { color: '#374151' } },
                axisLabel: { color: '#9ca3af', fontSize: 11 }
            },
            yAxis: {
                type: 'value',
                splitLine: { lineStyle: { color: '#1f2937' } },
                axisLabel: { color: '#9ca3af', fontSize: 11 }
            },
            series: []
        });

        // Responsive window resize
        window.addEventListener('resize', () => {
            if (chartInstance) chartInstance.resize();
        });
    }

    /**
     * Bind DOM controls
     */
    function bindEvents() {
        // Variable change
        const varSelect = document.getElementById('varSelect');
        if (varSelect) {
            varSelect.addEventListener('change', () => {
                updateVariableDescription();
                applyFilters();
                if (currentPoint) {
                    loadPointTimeSeries(currentPoint.lat, currentPoint.lon, currentPoint.marker);
                }
            });
        }

        // Date and Hour changes
        const dateSelect = document.getElementById('dateSelect');
        const hourSelect = document.getElementById('hourSelect');
        if (dateSelect) dateSelect.addEventListener('change', applyFilters);
        if (hourSelect) hourSelect.addEventListener('change', applyFilters);

        // Aggregation change
        const aggSelect = document.getElementById('aggSelect');
        const hourGroup = document.getElementById('hourGroup');
        if (aggSelect) {
            aggSelect.addEventListener('change', (e) => {
                if (e.target.value === 'hourly') {
                    if (hourGroup) hourGroup.style.display = 'block';
                } else {
                    if (hourGroup) hourGroup.style.display = 'none';
                }
                applyFilters();
            });
        }

        // Opacity Slider
        const opacityRange = document.getElementById('opacityRange');
        const opacityValue = document.getElementById('opacityValue');
        if (opacityRange) {
            opacityRange.addEventListener('input', (e) => {
                const val = e.target.value;
                if (opacityValue) opacityValue.textContent = `${val}%`;
                MapModule.setOpacity(parseFloat(val) / 100);
            });
        }

        // Smooth toggle
        const smoothToggle = document.getElementById('smoothToggle');
        if (smoothToggle) {
            smoothToggle.addEventListener('change', applyFilters);
        }

        // Layer toggles
        const layerRasterCheck = document.getElementById('layerRasterCheck');
        const layerWindCheck = document.getElementById('layerWindCheck');
        const layerBoundaryCheck = document.getElementById('layerBoundaryCheck');

        if (layerRasterCheck) {
            layerRasterCheck.addEventListener('change', (e) => {
                MapModule.toggleRaster(e.target.checked);
            });
        }
        if (layerWindCheck) {
            layerWindCheck.addEventListener('change', (e) => {
                MapModule.toggleWind(e.target.checked);
                if (e.target.checked) {
                    MapModule.updateWind(getCurrentTimestamp());
                }
            });
        }
        if (layerBoundaryCheck) {
            layerBoundaryCheck.addEventListener('change', (e) => {
                MapModule.toggleBoundary(e.target.checked);
            });
        }

        // Basemap Radio buttons
        const basemapRadios = document.querySelectorAll('input[name="basemapRadio"]');
        basemapRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                MapModule.setBasemap(e.target.value);
            });
        });

        // Apply Filter Button
        const btnApply = document.getElementById('btnApplyFilter');
        if (btnApply) btnApply.addEventListener('click', applyFilters);

        // Animation Player Buttons
        const btnPlay = document.getElementById('btnPlayPause');
        const btnNext = document.getElementById('btnNextStep');
        const btnPrev = document.getElementById('btnPrevStep');
        if (btnPlay) btnPlay.addEventListener('click', togglePlayAnimation);
        if (btnNext) btnNext.addEventListener('click', stepNext);
        if (btnPrev) btnPrev.addEventListener('click', stepPrev);

        // Map toolbar button
        const btnReset = document.getElementById('btnResetView');
        if (btnReset) btnReset.addEventListener('click', MapModule.resetView);

        // Drawer Controls
        const btnCloseDrawer = document.getElementById('btnCloseDrawer');
        const btnToggleStats = document.getElementById('btnToggleStats');
        const drawer = document.getElementById('analyticsDrawer');
        const drawerDrag = document.getElementById('drawerDragHandle');

        if (btnCloseDrawer) btnCloseDrawer.addEventListener('click', () => toggleDrawer(false));
        if (btnToggleStats) btnToggleStats.addEventListener('click', () => toggleDrawer());
        if (drawerDrag) drawerDrag.addEventListener('click', () => toggleDrawer());

        // Drawer aggregation switcher
        const chartAggButtons = document.querySelectorAll('#chartAggGroup .btn-pill');
        chartAggButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                chartAggButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const agg = btn.getAttribute('data-agg');
                if (currentPoint) {
                    loadPointTimeSeries(currentPoint.lat, currentPoint.lon, currentPoint.marker, agg);
                }
            });
        });

        // CSV Export button
        const btnExportCsv = document.getElementById('btnExportCsv');
        if (btnExportCsv) {
            btnExportCsv.addEventListener('click', exportCsv);
        }

        // Sidebar collapse button
        const btnToggleSidebar = document.getElementById('btnToggleSidebar');
        const sidebar = document.getElementById('sidebar');
        if (btnToggleSidebar && sidebar) {
            btnToggleSidebar.addEventListener('click', () => {
                sidebar.classList.toggle('collapsed');
                const icon = btnToggleSidebar.querySelector('i');
                if (icon) {
                    icon.classList.toggle('fa-chevron-left');
                    icon.classList.toggle('fa-chevron-right');
                }
                setTimeout(() => {
                    MapModule.getMap().invalidateSize();
                }, 300);
            });
        }

        // Fullscreen toggle
        const btnFullscreen = document.getElementById('btnFullscreen');
        if (btnFullscreen) {
            btnFullscreen.addEventListener('click', () => {
                if (!document.fullscreenElement) {
                    document.documentElement.requestFullscreen();
                } else {
                    document.exitFullscreen();
                }
            });
        }

        // Help Modal
        const btnHelp = document.getElementById('btnHelp');
        const btnCloseHelp = document.getElementById('btnCloseHelp');
        const helpModal = document.getElementById('helpModal');
        if (btnHelp && helpModal) {
            btnHelp.addEventListener('click', () => helpModal.classList.add('active'));
        }
        if (btnCloseHelp && helpModal) {
            btnCloseHelp.addEventListener('click', () => helpModal.classList.remove('active'));
        }
        if (helpModal) {
            helpModal.addEventListener('click', (e) => {
                if (e.target === helpModal) helpModal.classList.remove('active');
            });
        }
    }

    /**
     * Retrieve current formatted timestamp string (YYYY-MM-DDTHH:MM:SS)
     */
    function getCurrentTimestamp() {
        const date = document.getElementById('dateSelect')?.value || '2025-11-11';
        const hour = document.getElementById('hourSelect')?.value || '00:00:00';
        return `${date}T${hour}`;
    }

    /**
     * Load initial available times
     */
    async function loadInitialTimes() {
        try {
            const res = await fetch('/api/times?step=1');
            if (!res.ok) return;
            const data = await res.json();
            availableTimes = data.times || [];
        } catch (err) {
            console.error('Failed to load times:', err);
        }
    }

    /**
     * Apply all sidebar filters and update map raster overlay
     */
    async function applyFilters() {
        const variable = document.getElementById('varSelect')?.value || 't2m';
        const date = document.getElementById('dateSelect')?.value || '2025-11-11';
        const timeStr = getCurrentTimestamp();
        const aggregation = document.getElementById('aggSelect')?.value || 'hourly';
        const smooth = document.getElementById('smoothToggle')?.checked ?? true;

        const meta = await MapModule.updateRaster({
            variable,
            date,
            time: timeStr,
            aggregation,
            smooth
        });

        // Update wind layer if active
        const isWindActive = document.getElementById('layerWindCheck')?.checked;
        if (isWindActive) {
            MapModule.updateWind(timeStr);
        }
    }

    /**
     * Update descriptive text of variable
     */
    function updateVariableDescription() {
        const varSelect = document.getElementById('varSelect');
        const descEl = document.getElementById('varDesc');
        if (!varSelect || !descEl) return;

        const descriptions = {
            t2m: "Temperatur udara pada ketinggian 2 meter di atas permukaan tanah (°C).",
            d2m: "Titik embun udara 2 meter (°C) yang menunjukkan tingkat kelembaban udara.",
            tp: "Akumulasi curah hujan (mm) baik cair maupun padat yang mencapai permukaan.",
            pev: "Potensi evaporasi (mm), mengukur tingkat penguapan potensial dari permukaan.",
            ro: "Limpasan permukaan (runoff) air hujan menuju sistem sungai dan danau (mm).",
            sp: "Tekanan atmosfer pada permukaan tanah (hPa).",
            swvl1: "Kandungan air dalam tanah lapisan 1 (kedalaman 0 - 7 cm) dalam m³/m³.",
            swvl2: "Kandungan air dalam tanah lapisan 2 (kedalaman 7 - 28 cm) dalam m³/m³.",
            swvl3: "Kandungan air dalam tanah lapisan 3 (kedalaman 28 - 100 cm) dalam m³/m³.",
            swvl4: "Kandungan air dalam tanah lapisan 4 (kedalaman 100 - 289 cm) dalam m³/m³.",
            u10: "Komponen angin arah Timur-Barat (U) pada ketinggian 10 meter (m/s).",
            v10: "Komponen angin arah Utara-Selatan (V) pada ketinggian 10 meter (m/s).",
            wind_speed: "Kecepatan angin horizontal total (m/s) dihitung dari magnitudo U10 dan V10."
        };

        const val = varSelect.value;
        descEl.textContent = descriptions[val] || "Variabel meteorologi dan hidrologi ERA5-Land.";
    }

    /**
     * Time Series Player: Play/Pause animation
     */
    function togglePlayAnimation() {
        const btn = document.getElementById('btnPlayPause');
        if (isPlaying) {
            clearInterval(playInterval);
            isPlaying = false;
            if (btn) btn.innerHTML = '<i class="fa-solid fa-play"></i>';
        } else {
            isPlaying = true;
            if (btn) btn.innerHTML = '<i class="fa-solid fa-pause"></i>';
            playInterval = setInterval(stepNext, 1500);
        }
    }

    /**
     * Time Series Player: Step Next
     */
    function stepNext() {
        const hourSelect = document.getElementById('hourSelect');
        const dateSelect = document.getElementById('dateSelect');
        if (!hourSelect || !dateSelect) return;

        let curIdx = hourSelect.selectedIndex;
        if (curIdx < hourSelect.options.length - 1) {
            hourSelect.selectedIndex = curIdx + 1;
        } else {
            // Next day
            hourSelect.selectedIndex = 0;
            const curDate = new Date(dateSelect.value);
            curDate.setDate(curDate.getDate() + 1);
            const nextDateStr = curDate.toISOString().split('T')[0];
            if (nextDateStr <= dateSelect.max) {
                dateSelect.value = nextDateStr;
            } else {
                dateSelect.value = dateSelect.min;
            }
        }
        applyFilters();
    }

    /**
     * Time Series Player: Step Prev
     */
    function stepPrev() {
        const hourSelect = document.getElementById('hourSelect');
        const dateSelect = document.getElementById('dateSelect');
        if (!hourSelect || !dateSelect) return;

        let curIdx = hourSelect.selectedIndex;
        if (curIdx > 0) {
            hourSelect.selectedIndex = curIdx - 1;
        } else {
            // Prev day
            hourSelect.selectedIndex = hourSelect.options.length - 1;
            const curDate = new Date(dateSelect.value);
            curDate.setDate(curDate.getDate() - 1);
            const prevDateStr = curDate.toISOString().split('T')[0];
            if (prevDateStr >= dateSelect.min) {
                dateSelect.value = prevDateStr;
            } else {
                dateSelect.value = dateSelect.max;
            }
        }
        applyFilters();
    }

    /**
     * Extract and render point time series from clicked coordinates
     */
    async function loadPointTimeSeries(lat, lon, marker, customAgg = null) {
        currentPoint = { lat, lon, marker };

        const variable = document.getElementById('varSelect')?.value || 't2m';
        const activeAggBtn = document.querySelector('#chartAggGroup .btn-pill.active');
        const aggregation = customAgg || activeAggBtn?.getAttribute('data-agg') || 'hourly';

        toggleDrawer(true);

        const emptyState = document.getElementById('chartEmptyState');
        if (emptyState) emptyState.style.display = 'none';

        if (chartInstance) {
            chartInstance.showLoading({
                text: 'Mengekstrak time series...',
                color: '#06b6d4',
                textColor: '#f9fafb',
                maskColor: 'rgba(11, 15, 25, 0.7)'
            });
        }

        try {
            const query = new URLSearchParams({
                variable,
                lat: lat.toFixed(4),
                lon: lon.toFixed(4),
                aggregation
            });

            const res = await fetch(`/api/timeseries?${query.toString()}`);
            if (!res.ok) throw new Error(`Status ${res.status}`);
            const tsData = await res.json();

            // Update title & stats
            const titleEl = document.getElementById('chartTitle');
            const subEl = document.getElementById('chartSubtitle');
            if (titleEl) {
                titleEl.innerHTML = `<i class="fa-solid fa-chart-area"></i> Profil ${tsData.name} (${tsData.unit})`;
            }
            if (subEl) {
                subEl.innerHTML = `Koordinat: <strong>Lat ${tsData.latitude}°, Lon ${tsData.longitude}°</strong> | Agregasi: <strong>${tsData.aggregation}</strong>`;
            }

            // Update stats cards
            updateStatsCards(tsData.stats, tsData.unit, tsData.variable);

            // Update Map Popup
            if (marker && marker.getPopup()) {
                const curTimeStr = getCurrentTimestamp().replace('T', ' ').substring(0, 16);
                const matched = (tsData.data || []).find(d => d.time === curTimeStr) || tsData.data?.[0];
                const displayVal = (matched && matched.value !== null && matched.value !== undefined)
                    ? `${matched.value} ${tsData.unit}`
                    : '<span style="color:#9ca3af;font-size:0.78rem;">Di luar grid daratan (Lautan)</span>';

                marker.setPopupContent(`
                    <div class="popup-card">
                        <div class="popup-title">${tsData.name}</div>
                        <div class="popup-coords">Lat: ${tsData.latitude}°, Lon: ${tsData.longitude}°</div>
                        <div class="popup-val-row">
                            <span>Nilai Grid:</span>
                            <span class="popup-val-num">${displayVal}</span>
                        </div>
                    </div>
                `);
            }

            // Render ECharts
            renderChartSeries(tsData);

        } catch (err) {
            console.error('Failed to load point timeseries:', err);
            if (chartInstance) chartInstance.hideLoading();
        }
    }


    /**
     * Update mini statistics cards
     */
    function updateStatsCards(stats, unit, variableId) {
        const minEl = document.getElementById('statMin');
        const meanEl = document.getElementById('statMean');
        const maxEl = document.getElementById('statMax');
        const totalEl = document.getElementById('statTotal');
        const totalCard = document.getElementById('statTotalCard');

        if (minEl) minEl.textContent = stats.min !== null && stats.min !== undefined ? `${stats.min} ${unit}` : '-';
        if (meanEl) meanEl.textContent = stats.mean !== null && stats.mean !== undefined ? `${stats.mean} ${unit}` : '-';
        if (maxEl) maxEl.textContent = stats.max !== null && stats.max !== undefined ? `${stats.max} ${unit}` : '-';

        if (stats.total !== undefined && stats.total !== null && ['tp', 'pev', 'ro'].includes(variableId)) {
            if (totalCard) totalCard.style.display = 'flex';
            if (totalEl) totalEl.textContent = `${stats.total} ${unit}`;
        } else {
            if (totalCard) totalCard.style.display = 'none';
        }
    }

    /**
     * Render ECharts line chart with gradients and tooltips
     */
    function renderChartSeries(tsData) {
        if (!chartInstance) return;
        chartInstance.hideLoading();

        const xData = (tsData.data || []).map(d => d.time);
        const yData = (tsData.data || []).map(d => d.value);

        const isBarChart = ['tp', 'ro'].includes(tsData.variable);

        const option = {
            backgroundColor: 'transparent',
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(17, 24, 39, 0.95)',
                borderColor: '#374151',
                textStyle: { color: '#f9fafb' },
                formatter: (params) => {
                    const item = params[0];
                    if (!item) return '';
                    return `
                        <div style="font-size:12px; font-weight:600; margin-bottom:4px; color:#38bdf8;">${item.name}</div>
                        <div style="font-size:13px; font-family:'JetBrains Mono',monospace;">
                            ${tsData.name}: <strong>${item.value !== null ? item.value : 'N/A'} ${tsData.unit}</strong>
                        </div>
                    `;
                }
            },
            grid: {
                top: 25,
                bottom: 45,
                left: 65,
                right: 25
            },
            xAxis: {
                type: 'category',
                data: xData,
                axisLine: { lineStyle: { color: '#374151' } },
                axisLabel: { color: '#9ca3af', fontSize: 11 }
            },
            yAxis: {
                type: 'value',
                scale: true,
                splitLine: { lineStyle: { color: '#1f2937' } },
                axisLabel: {
                    color: '#9ca3af',
                    fontSize: 11,
                    formatter: `{value} ${tsData.unit}`
                }
            },
            dataZoom: [
                {
                    type: 'inside',
                    start: 0,
                    end: 100
                },
                {
                    type: 'slider',
                    start: 0,
                    end: 100,
                    height: 18,
                    bottom: 5,
                    borderColor: '#374151',
                    textStyle: { color: '#9ca3af' },
                    fillerColor: 'rgba(2, 132, 199, 0.2)'
                }
            ],
            series: [
                {
                    name: tsData.name,
                    type: isBarChart ? 'bar' : 'line',
                    smooth: true,
                    showSymbol: false,
                    itemStyle: {
                        color: isBarChart ? '#0284c7' : '#06b6d4'
                    },
                    areaStyle: isBarChart ? null : {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(6, 182, 212, 0.45)' },
                            { offset: 1, color: 'rgba(6, 182, 212, 0.02)' }
                        ])
                    },
                    lineStyle: {
                        width: 2.5,
                        color: '#06b6d4'
                    },
                    data: yData
                }
            ]
        };

        chartInstance.setOption(option, true);
    }

    /**
     * Open or close bottom analytics drawer
     */
    function toggleDrawer(forceOpen = null) {
        const drawer = document.getElementById('analyticsDrawer');
        if (!drawer) return;

        if (forceOpen === true) {
            drawer.classList.add('open');
        } else if (forceOpen === false) {
            drawer.classList.remove('open');
        } else {
            drawer.classList.toggle('open');
        }

        setTimeout(() => {
            if (chartInstance) chartInstance.resize();
        }, 360);
    }

    /**
     * Download CSV data for current point
     */
    function exportCsv() {
        if (!currentPoint) {
            alert('Pilih titik pada peta terlebih dahulu sebelum mengekspor data CSV.');
            return;
        }
        const variable = document.getElementById('varSelect')?.value || 't2m';
        const activeAggBtn = document.querySelector('#chartAggGroup .btn-pill.active');
        const aggregation = activeAggBtn?.getAttribute('data-agg') || 'hourly';

        const downloadUrl = `/api/download?variable=${variable}&lat=${currentPoint.lat}&lon=${currentPoint.lon}&aggregation=${aggregation}`;
        window.open(downloadUrl, '_blank');
    }

    return {
        init,
        loadPointTimeSeries,
        toggleDrawer
    };
})();

// Initialize on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
    Dashboard.init();
    window.Dashboard = Dashboard;
});

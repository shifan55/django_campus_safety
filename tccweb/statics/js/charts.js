/**
 * Chart.js integration for Safe Campus Platform
 * Handles data visualization for admin dashboard
 */

let monthlyChart;
let typeChart;
let statusChart;
let monthlyBreakdowns = [];
let typeBreakdowns = [];
let statusLabelsMap = {};

const STATUS_COLOR_MAP = {
    pending: { background: 'rgba(255, 193, 7, 0.85)', border: 'rgb(255, 193, 7)' },
    under_review: { background: 'rgba(13, 202, 240, 0.85)', border: 'rgb(13, 202, 240)' },
    resolved: { background: 'rgba(25, 135, 84, 0.85)', border: 'rgb(25, 135, 84)' },
    closed: { background: 'rgba(108, 117, 125, 0.85)', border: 'rgb(108, 117, 125)' },
};

const STATUS_COLOR_FALLBACKS = [
    { background: 'rgba(54, 162, 235, 0.75)', border: 'rgb(54, 162, 235)' },
    { background: 'rgba(255, 99, 132, 0.75)', border: 'rgb(255, 99, 132)' },
    { background: 'rgba(75, 192, 192, 0.75)', border: 'rgb(75, 192, 192)' },
    { background: 'rgba(153, 102, 255, 0.75)', border: 'rgb(153, 102, 255)' },
    { background: 'rgba(255, 159, 64, 0.75)', border: 'rgb(255, 159, 64)' },
];

/**
 * Format a status key into a readable label.
 * @param {string} statusKey
 * @returns {string}
 */
function formatStatusLabel(statusKey) {
    if (!statusKey) {
        return 'Unknown';
    }
    if (statusLabelsMap[statusKey]) {
        return statusLabelsMap[statusKey];
    }
    return statusKey
        .toString()
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

/**
 * Retrieve colour styles for a given status, falling back to palette when needed.
 * @param {string} statusKey
 * @param {number} index
 * @returns {{background: string, border: string}}
 */
function getStatusColors(statusKey, index = 0) {
    if (STATUS_COLOR_MAP[statusKey]) {
        return STATUS_COLOR_MAP[statusKey];
    }
    return STATUS_COLOR_FALLBACKS[index % STATUS_COLOR_FALLBACKS.length];
}

/**
 * Clear and hide the chart detail container.
 * @param {string} elementId
 */
function clearChartDetails(elementId) {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.classList.add('d-none');
    el.innerHTML = '';
}

/**
 * Render status pills for a drilldown summary.
 * @param {Object} statusCounts
 * @param {number} total
 * @returns {string}
 */
function renderStatusPills(statusCounts = {}, total = 0) {
    const entries = Object.entries(statusCounts);
    if (!entries.length) {
        return '<span class="text-muted">No data available.</span>';
    }

    let markup = '';
    entries.forEach(([statusKey, value], index) => {
        const count = Number(value) || 0;
        if (count <= 0) {
            return;
        }
        const percentage = total ? ((count / total) * 100).toFixed(1) : '0.0';
        const colors = getStatusColors(statusKey, index);
        const pill = `<span class="status-pill" style="border: 1px solid ${colors.border}; color: ${colors.border};">${formatStatusLabel(statusKey)} <span class="fw-normal">${count} (${percentage}%)</span></span>`;
        markup += pill;
    });

    return markup || '<span class="text-muted">No data available.</span>';
}

/**
 * Initialize all charts with provided data
 * @param {Array} monthlyData - Monthly report data
 * @param {Array} typeData - Report type distribution data
 */
function initializeCharts(monthlyData = [], typeData = [], statusLabels = {}) {
    statusLabelsMap = statusLabels || {};
    monthlyBreakdowns = [];
    typeBreakdowns = [];
    clearChartDetails('monthlyChartDetails');
    clearChartDetails('typeChartDetails');

    // Initialize monthly trends chart
    initMonthlyChart(monthlyData, statusLabelsMap);
    
    // Initialize report types chart
    initTypeChart(typeData, statusLabelsMap);
    
    // Initialize status distribution chart if container exists
    const statusContainer = document.getElementById('statusChart');
    if (statusContainer) {
        initStatusChart();
    }
    
    // Set up responsive behavior
    setupResponsiveCharts();
}

/**
 * Initialize monthly trends line chart
 * @param {Array} data - Monthly data array
 */
function initMonthlyChart(data, statusLabels = {}) {
    const ctx = document.getElementById('monthlyChart');
    if (!ctx) return;
    
    // Process data for Chart.js
    const processedData = processMonthlyData(data, statusLabels);
    monthlyBreakdowns = processedData.breakdowns;
    
    monthlyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: processedData.labels,
            datasets: processedData.datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Monthly Report Trends',
                    font: {
                        size: 16,
                        weight: 'bold'
                    }
                },
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 18,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0, 0, 0, 0.85)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: 'rgba(255, 255, 255, 0.45)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    displayColors: true,
                    callbacks: {
                        title: function(context) {
                            return `Month: ${context[0].label}`;
                        },
                        label: function(context) {
                            const value = context.parsed.y;
                            return `${context.dataset.label}: ${value}`;
                        },
                        footer: function(tooltipItems) {
                            if (!tooltipItems.length) return '';
                            const index = tooltipItems[0].dataIndex;
                            const breakdown = monthlyBreakdowns[index];
                            const total = breakdown?.total ?? 0;
                            return `Total: ${total} report${total === 1 ? '' : 's'}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    stacked: true,
                    title: {
                        display: true,
                        text: 'Month'
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    stacked: true,
                    title: {
                        display: true,
                        text: 'Number of Reports'
                    },
                    beginAtZero: true
                }
            },
            interaction: {
                mode: 'index',
                intersect: false
                },
            onClick: (event, elements) => {
                if (!elements.length) {
                    clearChartDetails('monthlyChartDetails');
                    return;
                }
                const index = elements[0].index;
                showMonthlyDrilldown(index);
            },
            onHover: (event, elements) => {
                const target = event.native?.target;
                if (target) {
                    target.style.cursor = elements.length ? 'pointer' : 'default';
                }
            }
        }
    });
}

/**
 * Initialize report types doughnut chart
 * @param {Array} data - Type distribution data
 */
function initTypeChart(data, statusLabels = {}) {
    const ctx = document.getElementById('typeChart');
    if (!ctx) return;
    
    // Process data for Chart.js
    const processedData = processTypeData(data, statusLabels);
    typeBreakdowns = processedData.breakdowns;
    
    typeChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: processedData.labels,
            datasets: [{
                data: processedData.data,
                backgroundColor: [
                    '#FF6384',
                    '#36A2EB',
                    '#FFCE56',
                    '#4BC0C0',
                    '#9966FF',
                    '#FF9F40'
                ],
                borderColor: '#fff',
                borderWidth: 2,
                hoverBorderWidth: 4,
                hoverOffset: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Report Type Distribution',
                    font: {
                        size: 16,
                        weight: 'bold'
                    }
                },
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: '#fff',
                    borderWidth: 1,
                    cornerRadius: 6,
                    displayColors: true,
                    callbacks: {
                        title: function(context) {
                            return `${context[0].label}`;
                        },
                        label: function(context) {
                            const value = context.parsed;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${value} reports (${percentage}%)`;
                            },
                        afterBody: function(context) {
                            if (!context.length) return [];
                            const index = context[0].dataIndex;
                            const breakdown = typeBreakdowns[index];
                            if (!breakdown || !breakdown.statuses) return [];
                            const total = breakdown.total || 0;
                            return Object.entries(breakdown.statuses)
                                .filter(([, value]) => value > 0)
                                .map(([statusKey, value]) => {
                                    const count = Number(value) || 0;
                                    const pct = total ? ((count / total) * 100).toFixed(1) : '0.0';
                                    return `${formatStatusLabel(statusKey)}: ${count} (${pct}%)`;
                                });
                        },
                        footer: function(context) {
                            if (!context.length) return '';
                            const index = context[0].dataIndex;
                            const breakdown = typeBreakdowns[index];
                            const total = breakdown?.total ?? 0;
                            return `Total: ${total} report${total === 1 ? '' : 's'}`;
                        }
                    }
                }
            },
            cutout: '60%',
            animation: {
                animateScale: true,
                animateRotate: true
                },
            onClick: (event, elements) => {
                if (!elements.length) {
                    clearChartDetails('typeChartDetails');
                    return;
                }
                const index = elements[0].index;
                showTypeDrilldown(index);
            },
            onHover: (event, elements) => {
                const target = event.native?.target;
                if (target) {
                    target.style.cursor = elements.length ? 'pointer' : 'default';
                }
            }
        }
    });
}

/**
 * Initialize status distribution chart
 */
function initStatusChart() {
    const ctx = document.getElementById('statusChart');
    if (!ctx) return;
    
    // This would typically get data from an API endpoint
    // For now, using sample structure
    const statusData = {
        labels: ['Pending', 'Under Review', 'Resolved', 'Closed'],
        data: [0, 0, 0, 0] // Will be populated with real data
    };
    
    statusChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: statusData.labels,
            datasets: [{
                label: 'Reports by Status',
                data: statusData.data,
                backgroundColor: [
                    'rgba(255, 193, 7, 0.8)',  // Warning - Pending
                    'rgba(13, 202, 240, 0.8)', // Info - Under Review
                    'rgba(25, 135, 84, 0.8)',  // Success - Resolved
                    'rgba(108, 117, 125, 0.8)' // Secondary - Closed
                ],
                borderColor: [
                    'rgb(255, 193, 7)',
                    'rgb(13, 202, 240)',
                    'rgb(25, 135, 84)',
                    'rgb(108, 117, 125)'
                ],
                borderWidth: 2,
                borderRadius: 4,
                borderSkipped: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Reports by Status',
                    font: {
                        size: 16,
                        weight: 'bold'
                    }
                },
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: '#fff',
                    borderWidth: 1,
                    cornerRadius: 6,
                    displayColors: false
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

/**
 * Process monthly data for chart consumption
 * @param {Array} rawData - Raw monthly data from backend
 * @returns {Object} Processed data with labels and values
 */
function processMonthlyData(rawData, statusLabels = {}) {
    const now = new Date();
    const labels = [];
    const totals = [];
    const breakdowns = [];

    let statuses = Object.keys(statusLabels || {});
    const discoveredStatuses = new Set();
    rawData.forEach(item => {
        if (item?.statuses) {
            Object.keys(item.statuses).forEach(status => discoveredStatuses.add(status));
        }
    });
    if (!statuses.length && discoveredStatuses.size) {
        statuses = Array.from(discoveredStatuses);
    }

    const datasetMap = {};
    statuses.forEach(status => {
        datasetMap[status] = [];
    });
    
    for (let i = 11; i >= 0; i--) {
        const date = new Date(now.getFullYear(), now.getMonth() - i, 1);
        const monthKey = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}`;
        const monthLabel = date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
        
        labels.push(monthLabel);

        const monthData = rawData.find(item => item.month === monthKey) || {};
        const statusCounts = monthData.statuses || {};
        const breakdownStatuses = {};
        let total = 0;

        if (statuses.length) {
            statuses.forEach(status => {
                const value = Number(statusCounts[status] ?? 0);
                datasetMap[status].push(value);
                breakdownStatuses[status] = value;
                total += value;
            });
        } else {
            const value = Number(monthData.count ?? 0);
            total = value;
        }

        totals.push(total);
        breakdowns.push({
            label: monthLabel,
            month: monthKey,
            total,
            statuses: statuses.length ? breakdownStatuses : { total }
        });
    }
    
    let datasets;
    if (statuses.length) {
        datasets = statuses.map((status, index) => {
            const values = datasetMap[status] || [];
            const colors = getStatusColors(status, index);
            const hasValues = values.some(point => point > 0);
            return {
                label: formatStatusLabel(status),
                data: values,
                backgroundColor: colors.background,
                borderColor: colors.border,
                borderWidth: 1,
                borderRadius: 4,
                maxBarThickness: 48,
                stack: 'status',
                hidden: !hasValues && statuses.length > 1
            };
        });
    } else {
        datasets = [{
            label: 'Reports Submitted',
            data: totals,
            backgroundColor: 'rgba(54, 162, 235, 0.65)',
            borderColor: 'rgb(54, 162, 235)',
            borderWidth: 1,
            borderRadius: 4,
            maxBarThickness: 48,
            stack: 'status'
        }];
    }


    return {
        ​labels,
        datasets,
        breakdowns
    };
}

/**
 * Process type data for chart consumption
 * @param {Array} rawData - Raw type data from backend
 * @returns {Object} Processed data with labels and values
 */
function processTypeData(rawData, statusLabels = {}) {
    const labels = [];
    const data = [];
    const breakdowns = [];

    let statuses = Object.keys(statusLabels || {});
    const discoveredStatuses = new Set();
    rawData.forEach(item => {
        if (item?.statuses) {
            Object.keys(item.statuses).forEach(status => discoveredStatuses.add(status));
        }
    });
    if (!statuses.length && discoveredStatuses.size) {
        statuses = Array.from(discoveredStatuses);
    }
    
    rawData.forEach(item => {
        // Convert snake_case to Title Case
        const label = item.type.split('_').map(word =>  
            word.charAt(0).toUpperCase() + word.slice(1)
        ).join(' ');
        
        labels.push(label);
        const count = Number(item.count ?? 0);
        data.push(count);

        const statusBreakdown = {};
        if (statuses.length) {
            statuses.forEach(status => {
                statusBreakdown[status] = Number(item.statuses?.[status] ?? 0);
            });
        } else if (item.statuses) {
            Object.entries(item.statuses).forEach(([status, value]) => {
                statusBreakdown[status] = Number(value ?? 0);
            });
        } else {
            statusBreakdown.total = count;
        }

        breakdowns.push({
            label,
            total: count,
            statuses: statusBreakdown
        });
    });
    
    // If no data, show placeholder
    if (labels.length === 0) {
        labels.push('No Data');
        data.push(1);
        breakdowns.push({
            label: 'No Data',
            total: 1,
            statuses: { total: 1 }
        });
    }
    
    return {
        labels: labels,
        data: data,
        breakdowns: breakdowns
    };
}

/**
 * Display a drilldown summary for a monthly data point.
 * @param {number} index
 */
function showMonthlyDrilldown(index) {
    if (!monthlyBreakdowns.length) return;
    const breakdown = monthlyBreakdowns[index];
    if (!breakdown) return;

    const detailsEl = document.getElementById('monthlyChartDetails');
    if (!detailsEl) return;

    const pills = renderStatusPills(breakdown.statuses, breakdown.total);
    detailsEl.innerHTML = `
        <strong>${breakdown.label}</strong><br>
        <span class="text-muted">Total Cases: ${breakdown.total}</span>
        <div class="mt-2 d-flex flex-wrap">${pills}</div>
    `;
    detailsEl.classList.remove('d-none');

    if (window.SafeCampus?.announceToScreenReader) {
        window.SafeCampus.announceToScreenReader(`${breakdown.label} breakdown displayed with ${breakdown.total} total cases`);
    }
}

/**
 * Display a drilldown summary for a report type.
 * @param {number} index
 */
function showTypeDrilldown(index) {
    if (!typeBreakdowns.length) return;
    const breakdown = typeBreakdowns[index];
    if (!breakdown) return;

    const detailsEl = document.getElementById('typeChartDetails');
    if (!detailsEl) return;

    const pills = renderStatusPills(breakdown.statuses, breakdown.total);
    detailsEl.innerHTML = `
        <strong>${breakdown.label}</strong><br>
        <span class="text-muted">Total Cases: ${breakdown.total}</span>
        <div class="mt-2 d-flex flex-wrap">${pills}</div>
    `;
    detailsEl.classList.remove('d-none');

    if (window.SafeCampus?.announceToScreenReader) {
        window.SafeCampus.announceToScreenReader(`${breakdown.label} distribution displayed with ${breakdown.total} total cases`);
    }
}

/**
 * Update chart data dynamically
 * @param {string} chartType - Type of chart to update
 * @param {Array} newData - New data to display
 */
function updateChartData(chartType, newData) {
    let chart;
    let processedData;
    
    switch (chartType) {
        case 'monthly':
            chart = monthlyChart;
            processedData = processMonthlyData(newData, statusLabelsMap);
            if (chart) {
                chart.data.labels = processedData.labels;
                chart.data.datasets = processedData.datasets;
                monthlyBreakdowns = processedData.breakdowns;
                clearChartDetails('monthlyChartDetails');
                chart.update('active');
            }
            break;
            
        case 'type':
            chart = typeChart;
            processedData = processTypeData(newData, statusLabelsMap);
            if (chart) {
                chart.data.labels = processedData.labels;
                chart.data.datasets[0].data = processedData.data;
                typeBreakdowns = processedData.breakdowns;
                clearChartDetails('typeChartDetails');
                chart.update('active');
            }
            break;
            
        case 'status':
            chart = statusChart;
            if (chart && newData.labels && newData.data) {
                chart.data.labels = newData.labels;
                chart.data.datasets[0].data = newData.data;
                chart.update('active');
            }
            break;
    }
    
    // Announce update to screen readers
    if (window.SafeCampus?.announceToScreenReader) {
        window.SafeCampus.announceToScreenReader(`${chartType} chart updated with new data`);
    }
}

/**
 * Setup responsive behavior for charts
 */
function setupResponsiveCharts() {
    // Handle window resize
    window.addEventListener('resize', debounce(function() {
        if (monthlyChart) monthlyChart.resize();
        if (typeChart) typeChart.resize();
        if (statusChart) statusChart.resize();
    }, 300));
    
    // Handle tab visibility changes to pause animations
    document.addEventListener('visibilitychange', function() {
        const charts = [monthlyChart, typeChart, statusChart];
        charts.forEach(chart => {
            if (chart) {
                if (document.hidden) {
                    chart.stop();
                } else {
                    chart.render();
                }
            }
        });
    });
}

/**
 * Refresh all charts with new data from API
 */
async function refreshCharts() {
    try {
        // Show loading indicators
        showChartLoading();
        
        // Fetch new data from API
        const response = await fetch('/api/reports-data');
        if (!response.ok) {
            throw new Error('Failed to fetch chart data');
        }
        
        const data = await response.json();
        
        if (data.status_labels) {
            statusLabelsMap = data.status_labels;
        }

        // Update charts
       updateChartData('monthly', data.monthly || []);
        updateChartData('type', data.types || []);
        
        // Hide loading indicators
        hideChartLoading();
        
        if (window.SafeCampus?.showNotification) {
            window.SafeCampus.showNotification('Charts updated successfully', 'success', 3000);
        }
        
    } catch (error) {
        console.error('Error refreshing charts:', error);
        hideChartLoading();
        
        if (window.SafeCampus?.showNotification) {
            window.SafeCampus.showNotification('Failed to update charts', 'error');
        }
    }
}

/**
 * Show loading indicators on charts
 */
function showChartLoading() {
    const chartContainers = ['monthlyChart', 'typeChart', 'statusChart'];
    
    chartContainers.forEach(id => {
        const container = document.getElementById(id)?.parentElement;
        if (container && !container.querySelector('.chart-loading')) {
            const overlay = document.createElement('div');
            overlay.className = 'chart-loading position-absolute top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center bg-white bg-opacity-75';
            overlay.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div>';
            container.style.position = 'relative';
            container.appendChild(overlay);
        }
    });
}

/**
 * Hide loading indicators on charts
 */
function hideChartLoading() {
    const loadingOverlays = document.querySelectorAll('.chart-loading');
    loadingOverlays.forEach(overlay => overlay.remove());
}

/**
 * Export chart as image
 * @param {string} chartType - Type of chart to export
 * @param {string} filename - Filename for the exported image
 */
function exportChart(chartType, filename) {
    let chart;
    
    switch (chartType) {
        case 'monthly':
            chart = monthlyChart;
            break;
        case 'type':
            chart = typeChart;
            break;
        case 'status':
            chart = statusChart;
            break;
    }
    
    if (chart) {
        const url = chart.toBase64Image();
        const link = document.createElement('a');
        link.download = filename || `${chartType}-chart.png`;
        link.href = url;
        link.click();
        
        if (window.SafeCampus?.showNotification) {
            window.SafeCampus.showNotification('Chart exported successfully', 'success', 3000);
        }
    }
}

/**
 * Utility function for debouncing
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = function() {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Expose functions globally
window.ChartFunctions = {
    initializeCharts,
    updateChartData,
    refreshCharts,
    exportChart
};

// Auto-refresh charts every 5 minutes if on admin dashboard
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('monthlyChart') || document.getElementById('typeChart')) {
        setInterval(refreshCharts, 300000); // 5 minutes
    }
});

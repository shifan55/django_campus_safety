/**
 * Chart.js integration for Safe Campus Platform
 * Handles data visualization for admin dashboard with interactive insights
 */

let monthlyChart;
let typeChart;
let statusPieChart;
let counselorStackedChart;
let outcomeStackedChart;
let timelineChart;
let statusLabelMap = {};

const STATUS_PALETTE = {
    pending: { background: 'rgba(255, 193, 7, 0.75)', border: 'rgb(255, 193, 7)' },
    under_review: { background: 'rgba(13, 202, 240, 0.75)', border: 'rgb(13, 202, 240)' },
    resolved: { background: 'rgba(25, 135, 84, 0.75)', border: 'rgb(25, 135, 84)' },
    default: { background: 'rgba(108, 117, 125, 0.75)', border: 'rgb(108, 117, 125)' }
};

if (typeof Chart !== 'undefined' && Chart.register) {
    const zoomPlugin = window['chartjs-plugin-zoom']?.default || window['chartjs-plugin-zoom'];
    if (zoomPlugin) {
        Chart.register(zoomPlugin);
    }
}

/**
 * Initialize all charts with provided data
 */
function initializeCharts(
    monthlyData = [],
    typeData = [],
    statusData = [],
    counselorData = [],
    outcomeData = [],
    timelineData = [],
    labelsMap = {}
) {
    statusLabelMap = labelsMap || {};

    initMonthlyChart(monthlyData);
    initTypeChart(typeData);
    initStatusPieChart(statusData);
    initCounselorStackedChart(counselorData);
    initOutcomeStackedChart(outcomeData);
    initTimelineChart(timelineData);

    updateInsight('Interactive Insights', [{ text: 'Hover or click on any chart element to reveal additional context about the data.' }]);

    setupResponsiveCharts();
}

/**
 * Initialize monthly trends line chart
 */
function initMonthlyChart(data) {
    const ctx = document.getElementById('monthlyChart');
    if (!ctx) return;

    const processed = processMonthlyData(data);

    if (monthlyChart) {
        monthlyChart.destroy();
    }

    monthlyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: processed.labels,
            datasets: [{
                label: 'Reports Submitted',
                data: processed.data,
                borderColor: 'rgb(54, 162, 235)',
                backgroundColor: 'rgba(54, 162, 235, 0.12)',
                borderWidth: 3,
                fill: true,
                tension: 0.35,
                pointBackgroundColor: 'rgb(54, 162, 235)',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 6,
                pointHoverRadius: 9
            }]
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
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: 'rgb(54, 162, 235)',
                    borderWidth: 1,
                    cornerRadius: 6,
                    displayColors: false,
                    callbacks: {
                        title(context) {
                            return `Month: ${context[0].label}`;
                        },
                        label(context) {
                            const value = context.parsed.y;
                            return `${formatNumber(value)} report${value !== 1 ? 's' : ''} submitted`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Month'
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Number of Reports'
                    },
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            },
            onHover: (event, activeElements) => {
                if (event?.native?.target) {
                    event.native.target.style.cursor = activeElements.length ? 'pointer' : 'default';
                }
            },
            onClick: (event, activeElements) => {
                if (!activeElements?.length) return;
                const index = activeElements[0].index;
                const label = monthlyChart.data.labels[index];
                const value = monthlyChart.data.datasets[0].data[index];
                updateInsight('Monthly Report Trends', [
                    { text: `${formatNumber(value)} report${value !== 1 ? 's' : ''} submitted in ${label}.`, color: 'rgb(54, 162, 235)' }
                ]);
            }
        }
    });

    monthlyChart.$rawData = processed;
}

/**
 * Initialize report types doughnut chart
 */
function initTypeChart(data) {
    const ctx = document.getElementById('typeChart');
    if (!ctx) return;

    const processed = processTypeData(data);

    if (typeChart) {
        typeChart.destroy();
    }

    typeChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: processed.labels,
            datasets: [{
                data: processed.data,
                backgroundColor: processed.colors,
                borderColor: '#fff',
                borderWidth: 2,
                hoverBorderWidth: 4
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
                        font: { size: 12 }
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
                        label(context) {
                            const value = context.parsed;
                            const total = processed.total || 0;
                            const percentage = total ? formatPercentage(value / total) : '0.0%';
                            return `${formatNumber(value)} reports (${percentage})`;
                        }
                    }
                }
            },
            cutout: '60%',
            animation: {
                animateScale: true,
                animateRotate: true
            },
            onHover: (event, activeElements) => {
                if (event?.native?.target) {
                    event.native.target.style.cursor = activeElements.length ? 'pointer' : 'default';
                }
            },
            onClick: (event, activeElements) => {
                if (!activeElements?.length) return;
                const element = activeElements[0];
                const label = typeChart.data.labels[element.index];
                const value = typeChart.data.datasets[0].data[element.index];
                const total = processed.total || 0;
                const percentage = total ? formatPercentage(value / total) : '0.0%';
                updateInsight('Report Type Distribution', [
                    { text: `${label}: ${formatNumber(value)} cases (${percentage})`, color: typeChart.data.datasets[0].backgroundColor[element.index] }
                ]);
            }
        }
    });

    typeChart.$total = processed.total;
}

/**
 * Initialize status distribution pie chart
 */
function initStatusPieChart(data) {
    const ctx = document.getElementById('statusPieChart');
    if (!ctx) return;

    const processed = processStatusData(data);

    if (statusPieChart) {
        statusPieChart.destroy();
    }

    statusPieChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: processed.labels,
            datasets: [{
                data: processed.data,
                backgroundColor: processed.colors,
                borderColor: '#fff',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Case Status Distribution',
                    font: {
                        size: 16,
                        weight: 'bold'
                    }
                },
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 20
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: '#fff',
                    borderWidth: 1,
                    callbacks: {
                        label(context) {
                            const value = context.parsed;
                            const total = processed.total || 0;
                            const percentage = total ? formatPercentage(value / total) : '0.0%';
                            return `${formatNumber(value)} cases (${percentage})`;
                        }
                    }
                }
            },
            cutout: '55%',
            onHover: (event, activeElements) => {
                if (event?.native?.target) {
                    event.native.target.style.cursor = activeElements.length ? 'pointer' : 'default';
                }
            },
            onClick: (event, activeElements) => {
                if (!activeElements?.length) return;
                const element = activeElements[0];
                const label = statusPieChart.data.labels[element.index];
                const value = statusPieChart.data.datasets[0].data[element.index];
                const color = statusPieChart.data.datasets[0].backgroundColor[element.index];
                const total = processed.total || 0;
                const percentage = total ? formatPercentage(value / total) : '0.0%';
                updateInsight('Case Status Distribution', [
                    { text: `${label}: ${formatNumber(value)} cases (${percentage})`, color }
                ]);
            }
        }
    });

    statusPieChart.$total = processed.total;
    statusPieChart.$hasRealData = processed.hasRealData;
}

/**
 * Initialize counselor stacked bar chart
 */
function initCounselorStackedChart(data) {
    const ctx = document.getElementById('counselorStackedChart');
    if (!ctx) return;

    const processed = processCounselorData(data);

    if (counselorStackedChart) {
        counselorStackedChart.destroy();
    }

    counselorStackedChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: processed.labels,
            datasets: processed.datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Counselor Performance Breakdown',
                    font: {
                        size: 16,
                        weight: 'bold'
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label(context) {
                            const label = context.dataset.label;
                            const value = context.parsed.y;
                            return `${label}: ${formatNumber(value)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    stacked: true,
                    grid: { display: false }
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    ticks: { stepSize: 1 }
                }
            },
            onHover: (event, activeElements) => {
                if (event?.native?.target) {
                    event.native.target.style.cursor = activeElements.length ? 'pointer' : 'default';
                }
            },
            onClick: (event, activeElements) => {
                if (!activeElements?.length) return;
                const { datasetIndex, index } = activeElements[0];
                const counselor = counselorStackedChart.data.labels[index];
                const statusKey = processed.statusKeys[datasetIndex];
                const value = counselorStackedChart.data.datasets[datasetIndex].data[index];
                const total = processed.totals[index] || 0;
                const percentage = total ? formatPercentage(value / total) : '0.0%';
                updateInsight('Counselor Performance', [
                    { text: counselor, color: '#0d6efd' },
                    { text: `${getStatusLabel(statusKey)}: ${formatNumber(value)} cases (${percentage})`, color: getStatusColor(statusKey) },
                    { text: `Total assigned: ${formatNumber(total)} cases` }
                ]);
            }
        }
    });

    counselorStackedChart.$rawData = processed;
}

/**
 * Initialize outcome stacked bar chart
 */
function initOutcomeStackedChart(data) {
    const ctx = document.getElementById('outcomeStackedChart');
    if (!ctx) return;

    const processed = processOutcomeData(data);

    if (outcomeStackedChart) {
        outcomeStackedChart.destroy();
    }

    outcomeStackedChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: processed.labels,
            datasets: processed.datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Case Outcomes by Month',
                    font: {
                        size: 16,
                        weight: 'bold'
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label(context) {
                            const label = context.dataset.label;
                            const value = context.parsed.y;
                            return `${label}: ${formatNumber(value)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    stacked: true,
                    grid: { display: false }
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    ticks: { stepSize: 1 }
                }
            },
            onHover: (event, activeElements) => {
                if (event?.native?.target) {
                    event.native.target.style.cursor = activeElements.length ? 'pointer' : 'default';
                }
            },
            onClick: (event, activeElements) => {
                if (!activeElements?.length) return;
                const { datasetIndex, index } = activeElements[0];
                const month = outcomeStackedChart.data.labels[index];
                const statusKey = processed.statusKeys[datasetIndex];
                const value = outcomeStackedChart.data.datasets[datasetIndex].data[index];
                const total = processed.totals[index] || 0;
                const percentage = total ? formatPercentage(value / total) : '0.0%';
                updateInsight('Case Outcomes by Month', [
                    { text: month, color: '#0d6efd' },
                    { text: `${getStatusLabel(statusKey)}: ${formatNumber(value)} cases (${percentage})`, color: getStatusColor(statusKey) },
                    { text: `Total cases: ${formatNumber(total)} in ${month}` }
                ]);
            }
        }
    });

    outcomeStackedChart.$rawData = processed;
}

/**
 * Initialize interactive timeline chart
 */
function initTimelineChart(data) {
    const ctx = document.getElementById('timelineChart');
    if (!ctx) return;

    const processed = processTimelineData(data);

    if (timelineChart) {
        timelineChart.destroy();
    }

    timelineChart = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: processed.datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            parsing: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Weekly Case Timeline',
                    font: {
                        size: 16,
                        weight: 'bold'
                    }
                },
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    intersect: false,
                    mode: 'index',
                    callbacks: {
                        title(context) {
                            return context[0].raw.label || context[0].label;
                        },
                        label(context) {
                            return `${context.dataset.label}: ${formatNumber(context.parsed.y)}`;
                        }
                    }
                },
                zoom: {
                    zoom: {
                        wheel: {
                            enabled: true
                        },
                        drag: {
                            enabled: true
                        },
                        mode: 'x'
                    },
                    pan: {
                        enabled: true,
                        mode: 'x'
                    },
                    limits: {
                        x: { minRange: 3 * 24 * 60 * 60 * 1000 }
                    }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'week',
                        tooltipFormat: 'MMM d, yyyy'
                    },
                    title: {
                        display: true,
                        text: 'Week'
                    }
                },
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Reports'
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'nearest'
            },
            onHover: (event, activeElements) => {
                if (event?.native?.target) {
                    event.native.target.style.cursor = activeElements.length ? 'pointer' : 'default';
                }
            },
            onClick: (event, activeElements) => {
                if (!activeElements?.length) return;
                const point = activeElements[0];
                const dataset = timelineChart.data.datasets[point.datasetIndex];
                const dataPoint = dataset.data[point.index];
                const statusKey = processed.statusKeys[point.datasetIndex];
                const weekLabel = dataPoint.label || dataset.label;
                const totals = processed.weeklyTotals[point.index] || 0;
                const percentage = totals ? formatPercentage(dataPoint.y / totals) : '0.0%';
                updateInsight('Weekly Timeline', [
                    { text: weekLabel, color: '#0d6efd' },
                    { text: `${dataset.label}: ${formatNumber(dataPoint.y)} cases (${percentage})`, color: getStatusColor(statusKey) },
                    { text: `Total reports this week: ${formatNumber(totals)}` }
                ]);
            }
        }
    });

    timelineChart.$rawData = processed;
}

/**
 * Process monthly data for chart consumption
 */
function processMonthlyData(rawData) {
    const months = [];
    const data = [];
    const now = new Date();

    for (let i = 11; i >= 0; i--) {
        const date = new Date(now.getFullYear(), now.getMonth() - i, 1);
        const monthKey = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}`;
        const monthLabel = date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });

        months.push(monthLabel);

        const monthData = rawData.find(item => item.month === monthKey);
        data.push(monthData ? monthData.count : 0);
    }

    return { labels: months, data };
}

/**
 * Process type data for chart consumption
 */
function processTypeData(rawData) {
    const labels = [];
    const data = [];
    const colors = [];
    let total = 0;

    rawData.forEach(item => {
        const label = item.type
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
        labels.push(label);
        data.push(item.count);
        total += item.count;
        colors.push(getPaletteColor(label, colors.length));
    });

    if (!labels.length) {
        labels.push('No Data');
        data.push(1);
        colors.push('rgba(108, 117, 125, 0.5)');
    }

    return { labels, data, colors, total, hasRealData: total > 0 };
}

/**
 * Process status data for chart consumption
 */
function processStatusData(rawData) {
    const labels = [];
    const data = [];
    const colors = [];
    let total = 0;

    rawData.forEach(item => {
        labels.push(item.label || getStatusLabel(item.status));
        data.push(item.count);
        colors.push(getStatusColor(item.status));
        total += item.count;
    });

    const hasRealData = total > 0;

    if (!labels.length) {
        labels.push('No Data');
        data.push(1);
        colors.push(getStatusColor('default'));
    }

    return { labels, data, colors, total, hasRealData };
}

/**
 * Process counselor data for stacked chart
 */
function processCounselorData(rawData) {
    const labels = rawData.map(item => item.name);
    let statusKeys = Object.keys(statusLabelMap || {});
    if (!statusKeys.length) {
        statusKeys = ['pending', 'under_review', 'resolved'];
    }

    const datasets = statusKeys.map(status => ({
        label: getStatusLabel(status),
        data: rawData.map(item => item[status] || 0),
        backgroundColor: getStatusColor(status),
        stack: 'status'
    }));

    const totals = rawData.map(item => item.total || 0);

    return { labels, datasets, statusKeys, totals };
}

/**
 * Process outcome data for stacked chart
 */
function processOutcomeData(rawData) {
    const labels = rawData.map(item => item.label || item.month);
    let statusKeys = Object.keys(statusLabelMap || {});
    if (!statusKeys.length) {
        statusKeys = ['pending', 'under_review', 'resolved'];
    }

    const datasets = statusKeys.map(status => ({
        label: getStatusLabel(status),
        data: rawData.map(item => item[status] || 0),
        backgroundColor: getStatusColor(status),
        stack: 'status'
    }));

    const totals = rawData.map(item => {
        return statusKeys.reduce((sum, key) => sum + (item[key] || 0), 0);
    });

    return { labels, datasets, statusKeys, totals };
}

/**
 * Process timeline data for multi-series line chart
 */
function processTimelineData(rawData) {
    let statusKeys = Object.keys(statusLabelMap || {});
    if (!statusKeys.length) {
        statusKeys = ['pending', 'under_review', 'resolved'];
    }

    const datasets = statusKeys.map(status => ({
        label: getStatusLabel(status),
        data: rawData.map(item => ({
            x: item.start,
            y: item[status] || 0,
            label: item.label
        })),
        borderColor: getStatusBorderColor(status),
        backgroundColor: getStatusColor(status),
        tension: 0.3,
        fill: false,
        pointRadius: 4,
        pointHoverRadius: 7,
        pointBackgroundColor: getStatusColor(status)
    }));

    const weeklyTotals = rawData.map(item => {
        return statusKeys.reduce((sum, key) => sum + (item[key] || 0), 0);
    });

    return { datasets, statusKeys, weeklyTotals };
}

/**
 * Update chart data dynamically
 */
function updateChartData(chartType, newData) {
    switch (chartType) {
        case 'monthly':
            if (!monthlyChart) return;
            const monthlyProcessed = processMonthlyData(newData);
            monthlyChart.data.labels = monthlyProcessed.labels;
            monthlyChart.data.datasets[0].data = monthlyProcessed.data;
            monthlyChart.update();
            break;
        case 'type':
            if (!typeChart) return;
            const typeProcessed = processTypeData(newData);
            typeChart.data.labels = typeProcessed.labels;
            typeChart.data.datasets[0].data = typeProcessed.data;
            typeChart.data.datasets[0].backgroundColor = typeProcessed.colors;
            typeChart.$total = typeProcessed.total;
            typeChart.update();
            break;
        case 'status':
            if (!statusPieChart) return;
            const statusProcessed = processStatusData(newData);
            statusPieChart.data.labels = statusProcessed.labels;
            statusPieChart.data.datasets[0].data = statusProcessed.data;
            statusPieChart.data.datasets[0].backgroundColor = statusProcessed.colors;
            statusPieChart.$total = statusProcessed.total;
            statusPieChart.update();
            break;
        case 'counselor':
            if (!counselorStackedChart) return;
            const counselorProcessed = processCounselorData(newData);
            counselorStackedChart.data.labels = counselorProcessed.labels;
            counselorStackedChart.data.datasets = counselorProcessed.datasets;
            counselorStackedChart.update();
            break;
        case 'outcome':
            if (!outcomeStackedChart) return;
            const outcomeProcessed = processOutcomeData(newData);
            outcomeStackedChart.data.labels = outcomeProcessed.labels;
            outcomeStackedChart.data.datasets = outcomeProcessed.datasets;
            outcomeStackedChart.update();
            break;
        case 'timeline':
            if (!timelineChart) return;
            const timelineProcessed = processTimelineData(newData);
            timelineChart.data.datasets = timelineProcessed.datasets;
            timelineChart.update();
            break;
    }
}

/**
 * Setup responsive behavior for charts
 */
function setupResponsiveCharts() {
    window.addEventListener('resize', debounce(function() {
        [monthlyChart, typeChart, statusPieChart, counselorStackedChart, outcomeStackedChart, timelineChart].forEach(chart => {
            if (chart) {
                chart.resize();
            }
        });
    }, 300));

    document.addEventListener('visibilitychange', function() {
        const charts = [monthlyChart, typeChart, statusPieChart, counselorStackedChart, outcomeStackedChart, timelineChart];
        charts.forEach(chart => {
            if (!chart) return;
            if (document.hidden) {
                chart.stop();
            } else {
                chart.render();
            }
        });
    });
}

/**
 * Refresh all charts with new data from API
 */
async function refreshCharts() {
    try {
        showChartLoading();

        const response = await fetch('/api/reports-data');
        if (!response.ok) {
            throw new Error('Failed to fetch chart data');
        }

        const data = await response.json();

        updateChartData('monthly', data.monthly || []);
        updateChartData('type', data.types || []);
        updateChartData('status', data.status || []);
        updateChartData('counselor', data.counselors || []);
        updateChartData('outcome', data.outcomes || []);
        updateChartData('timeline', data.timeline || []);

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

function refreshData() {
    return refreshCharts();
}

/**
 * Show loading indicators on charts
 */
function showChartLoading() {
    const chartContainers = [
        'monthlyChart',
        'typeChart',
        'statusPieChart',
        'counselorStackedChart',
        'outcomeStackedChart',
        'timelineChart'
    ];

    chartContainers.forEach(id => {
        const container = document.getElementById(id)?.parentElement;
        if (container && !container.querySelector('.chart-loading')) {
            const overlay = document.createElement('div');
            overlay.className = 'chart-loading position-absolute top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center bg-body bg-opacity-75';
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
    document.querySelectorAll('.chart-loading').forEach(overlay => overlay.remove());
}

/**
 * Export chart as image
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
            chart = statusPieChart;
            break;
        case 'counselor':
            chart = counselorStackedChart;
            break;
        case 'outcome':
            chart = outcomeStackedChart;
            break;
        case 'timeline':
            chart = timelineChart;
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
 * Update insights panel content
 */
function updateInsight(title, details = []) {
    const insightEl = document.getElementById('chartInsight');
    if (!insightEl) return;

    insightEl.innerHTML = '';

    const heading = document.createElement('div');
    heading.className = 'insight-title';
    heading.textContent = title;
    insightEl.appendChild(heading);

    if (!details.length) {
        const placeholder = document.createElement('div');
        placeholder.className = 'insight-detail';
        placeholder.textContent = 'Select a data point to surface contextual insights.';
        insightEl.appendChild(placeholder);
        return;
    }

    details.forEach(detail => {
        const line = document.createElement('div');
        line.className = 'insight-detail';

        if (detail.color) {
            const dot = document.createElement('span');
            dot.className = 'chart-legend-dot';
            dot.style.backgroundColor = detail.color;
            line.appendChild(dot);
        }

        const text = document.createElement('span');
        text.textContent = detail.text;
        line.appendChild(text);
        insightEl.appendChild(line);
    });
}

function formatPercentage(value) {
    const percentage = Number(value * 100);
    if (Number.isNaN(percentage)) {
        return '0.0%';
    }
    return `${percentage.toFixed(1)}%`;
}

function formatNumber(value) {
    return new Intl.NumberFormat('en-US').format(value || 0);
}

function getStatusLabel(status) {
    if (!status) return 'Status';
    const label = statusLabelMap?.[status];
    if (label) return label;
    return status
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

function getStatusColor(status) {
    return (STATUS_PALETTE[status] || STATUS_PALETTE.default).background;
}

function getStatusBorderColor(status) {
    return (STATUS_PALETTE[status] || STATUS_PALETTE.default).border;
}

function getPaletteColor(label, index) {
    const palette = [
        '#FF6384',
        '#36A2EB',
        '#FFCE56',
        '#4BC0C0',
        '#9966FF',
        '#FF9F40',
        '#2ecc71',
        '#f39c12'
    ];
    return palette[index % palette.length];
}

/**
 * Utility function for debouncing
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
    refreshData,
    exportChart
};

// Auto-refresh charts every 5 minutes if on admin dashboard
document.addEventListener('DOMContentLoaded', function() {
    if (
        document.getElementById('monthlyChart') ||
        document.getElementById('typeChart')
    ) {
        setInterval(refreshCharts, 300000);
    }
});

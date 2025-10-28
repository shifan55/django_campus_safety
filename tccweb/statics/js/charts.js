/**
 * Chart.js integration for Safe Campus Platform
 * Handles data visualization for admin dashboard
 */

let monthlyChart;
let typeChart;
let weeklyChart;
let statusChart;

/**
 * Initialize all charts with provided data
 * @param {Array} monthlyData - Monthly report data
 * @param {Array} typeData - Report type distribution data
 */
function initializeCharts(monthlyData = [], typeData = [], weeklyData = []) {
    // Initialize monthly trends chart
    initMonthlyChart(monthlyData);

    // Initialize report types chart
    initTypeChart(typeData);

    // Initialize weekly chart
    initWeeklyChart(weeklyData);
    
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
function initMonthlyChart(data) {
    const ctx = document.getElementById('monthlyChart');
    if (!ctx) return;
    
    // Process data for Chart.js
    const processedData = processMonthlyData(data);
    
    monthlyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: processedData.labels,
            datasets: [{
                label: 'Reports Submitted',
                data: processedData.data,
                borderColor: 'rgb(54, 162, 235)',
                backgroundColor: 'rgba(54, 162, 235, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: 'rgb(54, 162, 235)',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 6,
                pointHoverRadius: 8
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
                        title: function(context) {
                            return `Month: ${context[0].label}`;
                        },
                        label: function(context) {
                            const value = context.parsed.y;
                            return `${value} report${value !== 1 ? 's' : ''} submitted`;
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
            }
        }
    });
}

/**
 * Initialize report types doughnut chart
 * @param {Array} data - Type distribution data
 */
function initTypeChart(data) {
    const ctx = document.getElementById('typeChart');
    if (!ctx) return;
    
    // Process data for Chart.js
    const processedData = processTypeData(data);
    
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
                        }
                    }
                }
            },
            cutout: '60%',
            animation: {
                animateScale: true,
                animateRotate: true
            }
        }
    });
}

/**
 * Initialize weekly volume chart
 * @param {Array} data - Weekly data array
 */
function initWeeklyChart(data) {
    const ctx = document.getElementById('weeklyChart');
    if (!ctx) return;

    const processedData = processWeeklyData(data);

    weeklyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: processedData.labels,
            datasets: [{
                label: 'Reports Handled',
                data: processedData.data,
                backgroundColor: 'rgba(99, 102, 241, 0.6)',
                borderColor: 'rgb(99, 102, 241)',
                borderWidth: 2,
                borderRadius: 6,
                maxBarThickness: 36
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Reports Handled by Week',
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
                    borderColor: 'rgb(99, 102, 241)',
                    borderWidth: 1,
                    cornerRadius: 6,
                    callbacks: {
                        title: function(context) {
                            return `Week of ${context[0].label}`;
                        },
                        label: function(context) {
                            const value = context.parsed.y || 0;
                            return `${value} case${value !== 1 ? 's' : ''}`;
                        }
                    }
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
                        precision: 0
                    }
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
function processMonthlyData(rawData) {
    // Generate last 12 months
    const months = [];
    const data = [];
    const now = new Date();
    
    for (let i = 11; i >= 0; i--) {
        const date = new Date(now.getFullYear(), now.getMonth() - i, 1);
        const monthKey = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}`;
        const monthLabel = date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
        
        months.push(monthLabel);
        
        // Find matching data or default to 0
        const monthData = rawData.find(item => item.month === monthKey);
        data.push(monthData ? monthData.count : 0);
    }
    
    return {
        labels: months,
        data: data
    };
}

/**
 * Process type data for chart consumption
 * @param {Array} rawData - Raw type data from backend
 * @returns {Object} Processed data with labels and values
 */
function processTypeData(rawData) {
    const labels = [];
    const data = [];
    
    rawData.forEach(item => {
        // Convert snake_case to Title Case
        const label = item.type.split('_').map(word => 
            word.charAt(0).toUpperCase() + word.slice(1)
        ).join(' ');
        
        labels.push(label);
        data.push(item.count);
    });
    
    // If no data, show placeholder
    if (labels.length === 0) {
        labels.push('No Data');
        data.push(1);
    }
    
    return {
        labels: labels,
        data: data
    };
}

/**
 * Process weekly data for chart consumption
 * @param {Array} rawData - Raw weekly data from backend
 * @returns {Object} Processed data with labels and values
 */
function processWeeklyData(rawData) {
    const labels = [];
    const data = [];

    const now = new Date();
    const startOfWeek = new Date(now);
    startOfWeek.setHours(0, 0, 0, 0);
    // Align with Monday as first day of the week
    const day = startOfWeek.getDay();
    const diff = (day === 0 ? -6 : 1) - day;
    startOfWeek.setDate(startOfWeek.getDate() + diff);

    for (let i = 7; i >= 0; i--) {
        const weekStart = new Date(startOfWeek);
        weekStart.setDate(weekStart.getDate() - i * 7);
        const weekKey = weekStart.toISOString().slice(0, 10);

        const label = `${weekStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;

        labels.push(label);

        const weekData = rawData.find(item => item.week === weekKey);
        data.push(weekData ? weekData.count : 0);
    }

    return {
        labels,
        data
    };
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
            processedData = processMonthlyData(newData);
            if (chart) {
                chart.data.labels = processedData.labels;
                chart.data.datasets[0].data = processedData.data;
                chart.update('active');
            }
            break;
            
        case 'type':
            chart = typeChart;
            processedData = processTypeData(newData);
            if (chart) {
                chart.data.labels = processedData.labels;
                chart.data.datasets[0].data = processedData.data;
                chart.update('active');
            }
            break;

        case 'weekly':
            chart = weeklyChart;
            processedData = processWeeklyData(newData);
            if (chart) {
                chart.data.labels = processedData.labels;
                chart.data.datasets[0].data = processedData.data;
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
        if (weeklyChart) weeklyChart.resize();
        if (statusChart) statusChart.resize();
    }, 300));

    // Handle tab visibility changes to pause animations
    document.addEventListener('visibilitychange', function() {
        const charts = [monthlyChart, typeChart, weeklyChart, statusChart];
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
        
        // Update charts
        updateChartData('monthly', data.monthly);
        updateChartData('type', data.types);
        if (data.weekly) {
            updateChartData('weekly', data.weekly);
        }

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
    const chartContainers = ['monthlyChart', 'typeChart', 'weeklyChart', 'statusChart'];
    
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
        case 'weekly':
            chart = weeklyChart;
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

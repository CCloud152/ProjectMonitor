// Dashboard JavaScript

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化图表
    initCharts();
    
    // 加载初始数据
    loadDashboardData();
    
    // 设置定时刷新
    setInterval(loadDashboardData, 30000); // 每30秒刷新一次
});

// 初始化图表
function initCharts() {
    // 系统负载趋势图
    const loadCtx = document.getElementById('loadChart').getContext('2d');
    window.loadChart = new Chart(loadCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'CPU使用率',
                data: [],
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                tension: 0.1
            }, {
                label: '内存使用率',
                data: [],
                borderColor: 'rgb(255, 99, 132)',
                backgroundColor: 'rgba(255, 99, 132, 0.2)',
                tension: 0.1
            }, {
                label: '磁盘使用率',
                data: [],
                borderColor: 'rgb(153, 102, 255)',
                backgroundColor: 'rgba(153, 102, 255, 0.2)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100
                }
            }
        }
    });

    // 客户端状态饼图
    const statusCtx = document.getElementById('statusChart').getContext('2d');
    window.statusChart = new Chart(statusCtx, {
        type: 'doughnut',
        data: {
            labels: ['在线', '离线'],
            datasets: [{
                data: [0, 0],
                backgroundColor: [
                    'rgba(75, 192, 192, 0.8)',
                    'rgba(255, 159, 64, 0.8)'
                ]
            }]
        },
        options: {
            responsive: true
        }
    });
}

// 加载仪表板数据
async function loadDashboardData() {
    try {
        // 获取客户端列表
        const clientsResponse = await fetch('/api/clients');
        const clientsData = await clientsResponse.json();
        
        // 获取告警信息
        const alertsResponse = await fetch('/api/alert');
        const alertsData = await alertsResponse.json();
        
        // 获取实时数据
        const realtimeResponse = await fetch('/api/realtime');
        const realtimeData = await realtimeResponse.json();
        
        // 更新统计卡片
        updateStatCards(clientsData, alertsData, realtimeData);
        
        // 更新图表
        updateCharts(realtimeData);
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
    }
}

// 更新统计卡片
function updateStatCards(clients, alerts, realtime) {
    // 在线客户端数量
    const onlineCount = clients ? clients.length : 0;
    document.getElementById('online-count').textContent = onlineCount;
    
    // 离线客户端数量
    const offlineCount = alerts ? alerts.length : 0;
    document.getElementById('offline-count').textContent = offlineCount;
    
    // 平均CPU使用率
    const avgCpu = realtime && realtime.cluster ? realtime.cluster.cpu.toFixed(1) : 0;
    document.getElementById('avg-cpu').textContent = avgCpu + '%';
}

// 更新图表
function updateCharts(realtime) {
    if (!realtime || !realtime.time_series) return;
    
    const timeSeries = realtime.time_series;
    
    // 更新时间标签
    const labels = timeSeries.cpu.map(item => {
        const date = new Date(item.timestamp * 1000);
        return date.toLocaleTimeString();
    });
    
    // 更新负载趋势图
    window.loadChart.data.labels = labels;
    window.loadChart.data.datasets[0].data = timeSeries.cpu.map(item => item.value);
    window.loadChart.data.datasets[1].data = timeSeries.memory.map(item => item.value);
    window.loadChart.data.datasets[2].data = timeSeries.disk.map(item => item.value);
    window.loadChart.update();
    
    // 更新状态饼图
    const onlineCount = parseInt(document.getElementById('online-count').textContent);
    const offlineCount = parseInt(document.getElementById('offline-count').textContent);
    window.statusChart.data.datasets[0].data = [onlineCount, offlineCount];
    window.statusChart.update();
}
function plotDashboardPipelineChart(labels, data, counts) {
    var ctx = document.getElementById('dashboardPipelineChart').getContext('2d');

    var palette = [
        'rgba(54, 162, 235, 0.7)',
        'rgba(255, 206, 86, 0.7)',
        'rgba(75, 192, 192, 0.7)',
        'rgba(153, 102, 255, 0.7)',
        'rgba(255, 159, 64, 0.7)',
        'rgba(46, 204, 113, 0.7)',
        'rgba(231, 76, 60, 0.7)'
    ];

    var bgColors = labels.map(function(_, i) {
        return palette[i % palette.length];
    });

    var borderColors = bgColors.map(function(c) {
        return c.replace('0.7', '1');
    });

    new Chart(ctx, {
        type: 'horizontalBar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Pipeline Value',
                data: data,
                backgroundColor: bgColors,
                borderColor: borderColors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            legend: { display: false },
            tooltips: {
                callbacks: {
                    label: function(tooltipItem, chartData) {
                        var value = chartData.datasets[0].data[tooltipItem.index];
                        var count = counts[tooltipItem.index];
                        var formatted = '$ ' + value.toLocaleString(undefined, {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2
                        });
                        return formatted + ' (' + count + ' deal' + (count !== 1 ? 's' : '') + ')';
                    }
                }
            },
            scales: {
                xAxes: [{
                    ticks: {
                        beginAtZero: true,
                        callback: function(value) {
                            var ranges = [
                                { divider: 1e6, suffix: 'M' },
                                { divider: 1e3, suffix: 'k' }
                            ];
                            for (var i = 0; i < ranges.length; i++) {
                                if (value >= ranges[i].divider) {
                                    return '$' + (value / ranges[i].divider) + ranges[i].suffix;
                                }
                            }
                            return '$' + value;
                        }
                    }
                }],
                yAxes: [{
                    ticks: { beginAtZero: true }
                }]
            }
        }
    });
}

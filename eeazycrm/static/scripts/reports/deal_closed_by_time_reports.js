function plot_closed_by_time_revenue(elemId, labels, wonData, lostData) {
    var ctx = document.getElementById(elemId).getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Won Revenue',
                data: wonData,
                backgroundColor: 'rgba(40, 167, 69, 0.15)',
                borderColor: 'rgba(40, 167, 69, 0.9)',
                borderWidth: 2,
                fill: true,
                pointRadius: 3,
                pointHoverRadius: 5
            }, {
                label: 'Lost Revenue',
                data: lostData,
                backgroundColor: 'rgba(220, 53, 69, 0.10)',
                borderColor: 'rgba(220, 53, 69, 0.9)',
                borderWidth: 2,
                fill: true,
                pointRadius: 3,
                pointHoverRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            layout: { padding: { right: 12 } },
            tooltips: {
                mode: 'index',
                intersect: false,
                callbacks: {
                    label: function(item, data) {
                        var val = item.yLabel;
                        var ranges = [
                            { divider: 1e6, suffix: 'M' },
                            { divider: 1e3, suffix: 'k' }
                        ];
                        function fmt(n) {
                            for (var i = 0; i < ranges.length; i++) {
                                if (n >= ranges[i].divider) {
                                    return (n / ranges[i].divider).toFixed(1) + ranges[i].suffix;
                                }
                            }
                            return n.toFixed(2);
                        }
                        return data.datasets[item.datasetIndex].label + ': $ ' + fmt(val);
                    }
                }
            },
            scales: {
                xAxes: [{ display: true, gridLines: { display: false } }],
                yAxes: [{
                    ticks: {
                        beginAtZero: true,
                        callback: function(value) {
                            var ranges = [
                                { divider: 1e6, suffix: 'M' },
                                { divider: 1e3, suffix: 'k' }
                            ];
                            function fmt(n) {
                                for (var i = 0; i < ranges.length; i++) {
                                    if (n >= ranges[i].divider) {
                                        return (n / ranges[i].divider).toString() + ranges[i].suffix;
                                    }
                                }
                                return n;
                            }
                            return '$ ' + fmt(value);
                        }
                    }
                }]
            }
        }
    });
}

function plot_closed_by_time_volume(elemId, labels, wonData, lostData) {
    var ctx = document.getElementById(elemId).getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Won Count',
                data: wonData,
                backgroundColor: 'rgba(40, 167, 69, 0.55)',
                borderColor: 'rgba(40, 167, 69, 0.9)',
                borderWidth: 1
            }, {
                label: 'Lost Count',
                data: lostData,
                backgroundColor: 'rgba(220, 53, 69, 0.55)',
                borderColor: 'rgba(220, 53, 69, 0.9)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            layout: { padding: { right: 12 } },
            tooltips: { mode: 'index', intersect: false },
            scales: {
                xAxes: [{ display: true, gridLines: { display: false } }],
                yAxes: [{
                    ticks: {
                        beginAtZero: true,
                        stepSize: 1
                    }
                }]
            }
        }
    });
}

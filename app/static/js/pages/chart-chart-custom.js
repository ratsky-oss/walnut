'use strict';
$(document).ready(function() {
    // [ pie-chart ] start
    var bar = document.getElementById("chart-pie-1").getContext('2d');
    var theme_g1 = bar.createLinearGradient(100, 0, 300, 0);
    theme_g1.addColorStop(0, 'rgba(29, 233, 182, 0.9)');
    theme_g1.addColorStop(1, 'rgba(29, 196, 233, 0.9)');
    var theme_g2 = bar.createLinearGradient(100, 0, 300, 0);
    theme_g2.addColorStop(0, 'rgba(137, 159, 212, 0.9)');
    theme_g2.addColorStop(1, 'rgba(163, 137, 212, 0.9)');
    var data4 = {
        labels: [
            "Data 1",
            "Data 2",
            "Data 3"
        ],
        datasets: [{
            data: [30, 30, 40],
            backgroundColor: [
                theme_g1,
                theme_g2,
                "#04a9f5"
            ],
            hoverBackgroundColor: [
                theme_g1,
                theme_g2,
                "#04a9f5"
            ]
        }]
    };
    var myPieChart = new Chart(bar, {
        type: 'pie',
        data: data4,
        responsive: true,
        options: {
            maintainAspectRatio: false,
        }
    });
    // [ pie-chart ] end
});

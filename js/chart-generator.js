// js/chart-generator.js

const appChartGenerator = {
    createScoreDistributionChart: function(canvasId, data, metricName, label) {
        const ctx = document.getElementById(canvasId).getContext('2d');

        if (!data || data.length === 0) {
            console.warn(`No data provided for chart: ${label}`);
            ctx.font = "16px Arial";
            ctx.textAlign = "center";
            ctx.fillText("Dados não disponíveis para este gráfico.", ctx.canvas.width / 2, ctx.canvas.height / 2);
            return null;
        }

        const scores = data.map(item => item[metricName]).filter(score => score !== null && score !== undefined);

        if (scores.length === 0) {
            console.warn(`No valid scores found for metric ${metricName} in chart: ${label}`);
            ctx.font = "16px Arial";
            ctx.textAlign = "center";
            ctx.fillText("Pontuações não disponíveis para este gráfico.", ctx.canvas.width / 2, ctx.canvas.height / 2);
            return null;
        }

        const goodCount = scores.filter(score => score >= 0.9).length;
        const okCount = scores.filter(score => score >= 0.5 && score < 0.9).length;
        const badCount = scores.filter(score => score < 0.5).length;

        return new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Ruim (<50%)', 'Ok (50-89%)', 'Bom (>=90%)'],
                datasets: [{
                    label: label,
                    data: [badCount, okCount, goodCount],
                    backgroundColor: [
                        'rgba(248, 215, 218, 0.7)', // bad - light red (was #f8d7da)
                        'rgba(255, 243, 205, 0.7)', // ok - light yellow (was #fff3cd)
                        'rgba(200, 230, 201, 0.7)'  // good - light green (was #c8e6c9)
                    ],
                    borderColor: [
                        'rgba(220, 53, 69, 1)',
                        'rgba(255, 193, 7, 1)',
                        'rgba(40, 167, 69, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true, // Try true to see if it helps with sizing
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Número de Sites'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false // Or true, if you prefer the label to be in the legend
                    },
                    title: {
                        display: true,
                        text: label,
                        font: {
                            size: 16
                        }
                    }
                }
            }
        });
    },

    generateAllCharts: function(psiData) {
        if (!psiData || psiData.length === 0) {
            console.warn("No PSI data available to generate charts.");
            // Optionally display a message on all chart canvases
            ['performanceChart', 'accessibilityChart', 'seoChart', 'bestPracticesChart'].forEach(id => {
                const ctx = document.getElementById(id)?.getContext('2d');
                if (ctx) {
                    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height); // Clear previous content
                    ctx.font = "16px Arial";
                    ctx.textAlign = "center";
                    ctx.fillText("Dados gerais não disponíveis.", ctx.canvas.width / 2, ctx.canvas.height / 2);
                }
            });
            return;
        }
        this.createScoreDistributionChart('performanceChart', psiData, 'performance', 'Distribuição de Pontuações de Performance');
        this.createScoreDistributionChart('accessibilityChart', psiData, 'accessibility', 'Distribuição de Pontuações de Acessibilidade');
        this.createScoreDistributionChart('seoChart', psiData, 'seo', 'Distribuição de Pontuações de SEO');
        this.createScoreDistributionChart('bestPracticesChart', psiData, 'bestPractices', 'Distribuição de Pontuações de Boas Práticas');
    }
};

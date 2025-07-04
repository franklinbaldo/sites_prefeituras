// js/chart-generator.js

const appChartGenerator = {
  createScoreDistributionChart: function (canvasId, data, metricName, label) {
    const canvas = document.getElementById(canvasId);
    const ctx = canvas.getContext("2d");
    const fallbackMessageId = canvasId + "FallbackMessage";
    const fallbackElement = document.getElementById(fallbackMessageId);

    // Clear previous state
    if (fallbackElement) fallbackElement.style.display = "none";
    canvas.style.display = "block";

    if (!data || data.length === 0) {
      console.warn(`No data provided for chart: ${label}`);
      if (fallbackElement) {
        fallbackElement.textContent =
          "Dados não disponíveis para este gráfico.";
        fallbackElement.style.display = "block";
      }
      canvas.style.display = "none";
      return null;
    }

    const scores = data
      .map((item) => item[metricName])
      .filter((score) => score !== null && score !== undefined);

    if (scores.length === 0) {
      console.warn(
        `No valid scores found for metric ${metricName} in chart: ${label}`,
      );
      if (fallbackElement) {
        fallbackElement.textContent =
          "Pontuações não disponíveis para este gráfico.";
        fallbackElement.style.display = "block";
      }
      canvas.style.display = "none";
      return null;
    }

    const goodCount = scores.filter((score) => score >= 0.9).length;
    const okCount = scores.filter(
      (score) => score >= 0.5 && score < 0.9,
    ).length;
    const badCount = scores.filter((score) => score < 0.5).length;

    return new Chart(ctx, {
      type: "bar",
      data: {
        labels: ["Ruim (<50%)", "Ok (50-89%)", "Bom (>=90%)"],
        datasets: [
          {
            label: label,
            data: [badCount, okCount, goodCount],
            backgroundColor: [
              "rgba(248, 215, 218, 0.7)", // bad - light red (was #f8d7da)
              "rgba(255, 243, 205, 0.7)", // ok - light yellow (was #fff3cd)
              "rgba(200, 230, 201, 0.7)", // good - light green (was #c8e6c9)
            ],
            borderColor: [
              "rgba(220, 53, 69, 1)",
              "rgba(255, 193, 7, 1)",
              "rgba(40, 167, 69, 1)",
            ],
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true, // Try true to see if it helps with sizing
        scales: {
          y: {
            beginAtZero: true,
            title: {
              display: true,
              text: "Número de Sites",
            },
          },
        },
        plugins: {
          legend: {
            display: false, // Or true, if you prefer the label to be in the legend
          },
          title: {
            display: true,
            text: label,
            font: {
              size: 16,
            },
          },
        },
      },
    });
  },

  generateAllCharts: function (psiData) {
    const chartConfigs = [
      {
        id: "performanceChart",
        metric: "performance",
        label: "Distribuição de Pontuações de Performance",
      },
      {
        id: "accessibilityChart",
        metric: "accessibility",
        label: "Distribuição de Pontuações de Acessibilidade",
      },
      {
        id: "seoChart",
        metric: "seo",
        label: "Distribuição de Pontuações de SEO",
      },
      {
        id: "bestPracticesChart",
        metric: "bestPractices",
        label: "Distribuição de Pontuações de Boas Práticas",
      },
    ];

    if (!psiData || psiData.length === 0) {
      console.warn("No PSI data available to generate charts.");
      chartConfigs.forEach((config) => {
        const canvas = document.getElementById(config.id);
        const fallbackElement = document.getElementById(
          config.id + "FallbackMessage",
        );
        if (canvas) canvas.style.display = "none";
        if (fallbackElement) {
          fallbackElement.textContent =
            "Dados gerais não disponíveis para gráficos.";
          fallbackElement.style.display = "block";
        }
      });
      return;
    }

    chartConfigs.forEach((config) => {
      this.createScoreDistributionChart(
        config.id,
        psiData,
        config.metric,
        config.label,
      );
    });
  },
};

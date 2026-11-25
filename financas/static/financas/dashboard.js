(function () {
    var tela = document.getElementById("grafico-mensal");
    var fonte = document.getElementById("dados-mensais");
    if (!tela || !fonte || typeof Chart === "undefined") {
        return;
    }
    var dados = JSON.parse(fonte.textContent);
    var moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
    Chart.defaults.color = "#a9a7a3";
    Chart.defaults.borderColor = "#3d3d3d";
    new Chart(tela, {
        type: "bar",
        data: {
            labels: dados.map(function (d) { return d.mes; }),
            datasets: [
                { label: "Receitas", data: dados.map(function (d) { return d.receitas; }), backgroundColor: "#adc0cf" },
                { label: "Despesas", data: dados.map(function (d) { return d.despesas; }), backgroundColor: "#d6a77b" }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: { callbacks: { label: function (c) { return c.dataset.label + ": " + moeda.format(c.parsed.y); } } }
            },
            scales: { y: { beginAtZero: true, ticks: { callback: function (v) { return moeda.format(v); } } } }
        }
    });
})();

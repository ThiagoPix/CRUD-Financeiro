(function () {
    var fonte = document.getElementById("dados-graficos");
    if (!fonte || typeof Chart === "undefined") {
        return;
    }
    var dados = JSON.parse(fonte.textContent);
    var moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

    var AZUL = "#adc0cf";
    var COBRE = "#d6a77b";
    var VERDE = "#b9c79a";
    var ALERTA = "#eea18d";

    Chart.defaults.color = "#a9a7a3";
    Chart.defaults.borderColor = "#3d3d3d";
    Chart.defaults.font.family = '"Segoe UI", Arial, sans-serif';

    function valores(lista, campo) {
        return lista.map(function (item) { return item[campo]; });
    }

    function eixoMoeda(extra) {
        var eixo = { beginAtZero: true, ticks: { callback: function (v) { return moeda.format(v); } } };
        for (var chave in (extra || {})) { eixo[chave] = extra[chave]; }
        return eixo;
    }

    // Tooltip em reais, para barras verticais (y) e horizontais (x)
    var tooltipMoeda = {
        callbacks: {
            label: function (contexto) {
                var valor = contexto.chart.options.indexAxis === "y" ? contexto.parsed.x : contexto.parsed.y;
                return contexto.dataset.label + ": " + moeda.format(valor);
            }
        }
    };

    function desenhar(id, lista, montar) {
        var tela = document.getElementById(id);
        if (tela && lista && lista.length) {
            new Chart(tela, montar(lista));
        }
    }

    function barrasHorizontais(rotulo, campo, cor) {
        return function (lista) {
            return {
                type: "bar",
                data: {
                    labels: valores(lista, "nome"),
                    datasets: [{ label: rotulo, data: valores(lista, campo), backgroundColor: cor }]
                },
                options: {
                    indexAxis: "y",
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false }, tooltip: tooltipMoeda },
                    scales: { x: eixoMoeda() }
                }
            };
        };
    }

    // 1. Recebido x pago por mês, com o saldo realizado acumulado em linha
    desenhar("grafico-fluxo", dados.fluxo, function (lista) {
        return {
            type: "bar",
            data: {
                labels: valores(lista, "mes"),
                datasets: [
                    { label: "Recebido", data: valores(lista, "recebido"), backgroundColor: AZUL },
                    { label: "Pago", data: valores(lista, "pago"), backgroundColor: COBRE },
                    {
                        type: "line", label: "Saldo realizado acumulado", data: valores(lista, "saldo_acumulado"),
                        borderColor: VERDE, backgroundColor: VERDE, tension: 0.25, pointRadius: 3
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { tooltip: tooltipMoeda },
                scales: { y: eixoMoeda({ beginAtZero: false }) }
            }
        };
    });

    // 2. O que ainda vem pela frente: a receber x a pagar, empilhado por mês
    desenhar("grafico-previsao", dados.previsao, function (lista) {
        return {
            type: "bar",
            data: {
                labels: valores(lista, "mes"),
                datasets: [
                    { label: "A receber", data: valores(lista, "a_receber"), backgroundColor: AZUL },
                    { label: "A pagar", data: valores(lista, "a_pagar"), backgroundColor: COBRE }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { tooltip: tooltipMoeda },
                scales: { x: { stacked: true }, y: eixoMoeda({ stacked: true }) }
            }
        };
    });

    // 3 a 5. Rankings e distribuição em barras horizontais
    desenhar("grafico-despesas-categoria", dados.despesas_categoria, barrasHorizontais("Despesas", "total", COBRE));
    desenhar("grafico-receitas-categoria", dados.receitas_categoria, barrasHorizontais("Receitas", "total", AZUL));
    desenhar("grafico-despesas-conta", dados.despesas_conta, barrasHorizontais("Despesas", "total", COBRE));

    // 6. Saldo atual por conta (negativo em alerta)
    desenhar("grafico-saldo-contas", dados.contas, function (lista) {
        return {
            type: "bar",
            data: {
                labels: valores(lista, "nome"),
                datasets: [{
                    label: "Saldo atual",
                    data: valores(lista, "saldo"),
                    backgroundColor: valores(lista, "saldo").map(function (v) { return v < 0 ? ALERTA : VERDE; })
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false }, tooltip: tooltipMoeda },
                scales: { y: eixoMoeda({ beginAtZero: false }) }
            }
        };
    });

    // 7. Orçamento do mês: limite x gasto (estourado em alerta)
    desenhar("grafico-orcamentos", dados.orcamentos, function (lista) {
        return {
            type: "bar",
            data: {
                labels: valores(lista, "nome"),
                datasets: [
                    { label: "Limite", data: valores(lista, "limite"), backgroundColor: AZUL },
                    {
                        label: "Gasto (pago)",
                        data: valores(lista, "gasto"),
                        backgroundColor: lista.map(function (i) { return i.gasto > i.limite ? ALERTA : COBRE; })
                    }
                ]
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: { tooltip: tooltipMoeda },
                scales: { x: eixoMoeda() }
            }
        };
    });
})();

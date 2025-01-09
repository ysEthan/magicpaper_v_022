function initDashboardCharts(data) {
    // 商品趋势图
    var productTrendChart = new ApexCharts(document.querySelector("#product-trend"), {
        chart: {
            type: 'area',
            height: 120,
            sparkline: {
                enabled: true
            }
        },
        stroke: {
            width: 2,
            curve: 'smooth'
        },
        fill: {
            opacity: 0.16
        },
        series: [{
            name: '商品数量',
            data: data.product_trend
        }],
        yaxis: {
            min: 0,
            labels: {
                formatter: function(val) {
                    return Math.round(val);
                }
            }
        },
        colors: ['#206bc4'],
        title: {
            text: data.total_products,
            offsetX: 0,
            style: {
                fontSize: '22px'
            }
        },
        subtitle: {
            text: '商品总数',
            offsetX: 0,
            style: {
                fontSize: '14px'
            }
        }
    });
    productTrendChart.render();

    // 订单趋势图
    var orderTrendChart = new ApexCharts(document.querySelector("#order-trend"), {
        chart: {
            type: 'area',
            height: 120,
            sparkline: {
                enabled: true
            }
        },
        stroke: {
            width: 2,
            curve: 'smooth'
        },
        fill: {
            opacity: 0.16
        },
        series: [{
            name: '销售额',
            data: data.order_trend
        }],
        yaxis: {
            min: 0,
            labels: {
                formatter: function(val) {
                    return '$ ' + val.toFixed(2);
                }
            }
        },
        colors: ['#206bc4'],
        title: {
            text: '$ ' + data.month_sales.toFixed(2),
            offsetX: 0,
            style: {
                fontSize: '22px'
            }
        },
        subtitle: {
            text: '本月销售额',
            offsetX: 0,
            style: {
                fontSize: '14px'
            }
        }
    });
    orderTrendChart.render();

    // 物流趋势图
    var logisticsTrendChart = new ApexCharts(document.querySelector("#logistics-trend"), {
        chart: {
            type: 'area',
            height: 120,
            sparkline: {
                enabled: true
            }
        },
        stroke: {
            width: 2,
            curve: 'smooth'
        },
        fill: {
            opacity: 0.16
        },
        series: [{
            name: '运费',
            data: data.logistics_trend
        }],
        yaxis: {
            min: 0,
            labels: {
                formatter: function(val) {
                    return '$ ' + val.toFixed(2);
                }
            }
        },
        colors: ['#206bc4'],
        title: {
            text: '$ ' + data.month_shipping_cost.toFixed(2),
            offsetX: 0,
            style: {
                fontSize: '22px'
            }
        },
        subtitle: {
            text: '本月运费',
            offsetX: 0,
            style: {
                fontSize: '14px'
            }
        }
    });
    logisticsTrendChart.render();

    // 采购趋势图
    var purchaseTrendChart = new ApexCharts(document.querySelector("#purchase-trend"), {
        chart: {
            type: 'area',
            height: 120,
            sparkline: {
                enabled: true
            }
        },
        stroke: {
            width: 2,
            curve: 'smooth'
        },
        fill: {
            opacity: 0.16
        },
        series: [{
            name: '采购额',
            data: data.purchase_trend
        }],
        yaxis: {
            min: 0,
            labels: {
                formatter: function(val) {
                    return '$ ' + val.toFixed(2);
                }
            }
        },
        colors: ['#206bc4'],
        title: {
            text: '$ ' + data.month_purchase.toFixed(2),
            offsetX: 0,
            style: {
                fontSize: '22px'
            }
        },
        subtitle: {
            text: '本月采购额',
            offsetX: 0,
            style: {
                fontSize: '14px'
            }
        }
    });
    purchaseTrendChart.render();

    // 库存趋势图
    var inventoryTrendChart = new ApexCharts(document.querySelector("#inventory-trend"), {
        chart: {
            type: 'area',
            height: 120,
            sparkline: {
                enabled: true
            }
        },
        stroke: {
            width: 2,
            curve: 'smooth'
        },
        fill: {
            opacity: 0.16
        },
        series: [{
            name: '库存总值',
            data: data.inventory_trend
        }],
        yaxis: {
            min: 0,
            labels: {
                formatter: function(val) {
                    return '$ ' + val.toFixed(2);
                }
            }
        },
        colors: ['#206bc4'],
        title: {
            text: '$ ' + data.total_inventory_value.toFixed(2),
            offsetX: 0,
            style: {
                fontSize: '22px'
            }
        },
        subtitle: {
            text: '库存总值',
            offsetX: 0,
            style: {
                fontSize: '14px'
            }
        }
    });
    inventoryTrendChart.render();
}
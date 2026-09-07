{
    "name": "Sale Stock Availability Color",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "summary": "Color the sales stock widget by on-hand vs forecasted qty",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": ["sale_stock"],
    "data": ["views/sale_order_views.xml"],
    "assets": {
        "web.assets_backend": [
            "sale_stock_availability_color/static/src/widgets/qty_at_date_widget.js",
            "sale_stock_availability_color/static/src/widgets/qty_at_date_widget.xml",
            "sale_stock_availability_color/static/src/widgets/qty_at_date_widget.scss",
        ],
    },
    "installable": True,
    "application": False,
}

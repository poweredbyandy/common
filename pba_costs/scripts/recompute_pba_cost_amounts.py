#!/usr/bin/env python3
"""Recalcula importes PBA (flete/arancel/operativo/nacionalización) con último costo × %.

Uso A — Odoo shell (recomendado, en el servidor):

    ./odoo-bin shell -c odoo.conf -d NOMBRE_BD
    >>> env['product.template'].pba_recompute_cost_amounts_from_last_cost()
    >>> env.cr.commit()

Uso B — XML-RPC (después de actualizar el módulo con el método):

    python3 custom/common/pba_costs/scripts/recompute_pba_cost_amounts.py \\
        --url https://gasacave.com --db gasacave.com --user admin --password admin

También se ejecuta solo al actualizar pba_costs a 18.0.1.10.1 (post-migrate).
"""

from __future__ import annotations

import argparse
import sys
import xmlrpc.client


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Recalcula importes PBA desde pba_last_cost vía XML-RPC",
    )
    parser.add_argument("--url", required=True, help="URL base Odoo, ej. https://gasacave.com")
    parser.add_argument("--db", required=True, help="Nombre de la base de datos")
    parser.add_argument("--user", default="admin")
    parser.add_argument("--password", required=True)
    parser.add_argument(
        "--ids",
        default="",
        help="IDs de product.template separados por coma (opcional; si vacío, todos con % PBA)",
    )
    args = parser.parse_args(argv)

    url = args.url.rstrip("/")
    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
    uid = common.authenticate(args.db, args.user, args.password, {})
    if not uid:
        print("ERROR: autenticación fallida", file=sys.stderr)
        return 1

    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
    template_ids = None
    if args.ids.strip():
        template_ids = [int(x) for x in args.ids.split(",") if x.strip()]

    count = models.execute_kw(
        args.db,
        uid,
        args.password,
        "product.template",
        "pba_recompute_cost_amounts_from_last_cost",
        [template_ids],
    )
    print(f"Recalculados: {count} producto(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

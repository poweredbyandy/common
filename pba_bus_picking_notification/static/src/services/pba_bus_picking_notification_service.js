/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

export const pbaBusPickingNotificationService = {
    dependencies: ["bus_service", "notification", "action"],

    async start(env, { bus_service: busService, notification, action }) {
        const hasGroup = await user.hasGroup(
            "pba_bus_picking_notification.group_stock_picking_bus_notify"
        );
        if (!hasGroup) {
            return {};
        }
        busService.subscribe("pba.stock.picking/created", (payload) => {
            const pickingId = payload.picking_id;
            const name = payload.name || "";
            const typeName = payload.picking_type_name || "";
            const bodyParts = [name];
            if (typeName) {
                bodyParts.push(typeName);
            }
            notification.add(bodyParts.filter(Boolean).join(" · "), {
                title: _t("Nuevo picking pendiente"),
                type: "info",
                sticky: true,
                buttons: pickingId
                    ? [
                          {
                              name: _t("Abrir"),
                              primary: true,
                              onClick: () => {
                                  action.doAction({
                                      type: "ir.actions.act_window",
                                      res_model: "stock.picking",
                                      res_id: pickingId,
                                      views: [[false, "form"]],
                                      target: "current",
                                  });
                              },
                          },
                      ]
                    : [],
            });
        });
        await busService.start();
        return {};
    },
};

registry.category("services").add("pba_bus_picking_notification", pbaBusPickingNotificationService);

import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { session } from "@web/session";
import { user } from "@web/core/user";

function emptyState() {
    return {
        enabled: false,
        required: false,
        locked: false,
        current_sub_user_id: false,
        current_sub_user_name: false,
        sub_users: [],
    };
}

export const subUserService = {
    dependencies: ["notification"],
    start(env, { notification }) {
        const initial = session.res_users_user || emptyState();
        const state = reactive({ ...initial });

        function applyPayload(payload) {
            Object.assign(state, payload || emptyState());
            if (state.current_sub_user_id) {
                user.updateContext({ sub_user_id: state.current_sub_user_id });
            } else {
                user.updateContext({ sub_user_id: false });
            }
        }

        applyPayload(initial);

        return {
            state,
            get enabled() {
                return state.enabled;
            },
            get locked() {
                return state.locked;
            },
            get currentName() {
                return state.current_sub_user_name || "";
            },
            async refresh() {
                const payload = await rpc("/res_users_user/session");
                applyPayload(payload);
                return payload;
            },
            async login(subUserId, pin) {
                try {
                    const payload = await rpc("/res_users_user/login", {
                        sub_user_id: subUserId,
                        pin,
                    });
                    applyPayload(payload);
                    return payload;
                } catch (error) {
                    notification.add(error.data?.message || error.message, {
                        type: "danger",
                    });
                    throw error;
                }
            },
            async lock() {
                const payload = await rpc("/res_users_user/lock");
                applyPayload(payload);
                return payload;
            },
        };
    },
};

registry.category("services").add("sub_user", subUserService);
